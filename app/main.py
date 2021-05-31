#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from datetime import datetime, timedelta

# 3rd party:
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from opencensus.trace.samplers import AlwaysOnSampler
from opencensus.ext.azure.log_exporter import AzureLogHandler

# Internal:
from app.postcode.views import postcode_page
from app.landing.views import home_page
from app.healthcheck.views import run_healthcheck
from app.config import Settings
from app.common.utils import add_cloud_role_name
from app.middleware.tracers.starlette import TraceRequestMiddleware
from app.middleware.headers import ProxyHeadersHostMiddleware
from app.middleware.tracers.azure.exporter import Exporter
from app.exceptions import exception_handlers
from app import generic
from app.context import redis

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'app'
]


HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

from os import environ
from json import dumps

print(Settings.instrumentation_key)
print("ENV VARS: " + dumps({
    key: value[:2] if value else None
    for key, value in environ.items()
}))


routes = [
    Route('/', endpoint=home_page, methods=["GET"]),
    Route(f'/{Settings.healthcheck_path}', endpoint=run_healthcheck, methods=["GET", "HEAD"]),
    Route('/search', endpoint=postcode_page, methods=["GET"]),
    Mount('/assets', StaticFiles(directory="assets"), name="static"),
    Route('/favicon.ico', endpoint=generic.favicon_ico),
    Route('/favicon.png', endpoint=generic.favicon_png),
    Route('/sitemap.xml', endpoint=generic.sitemap),
]


logging_instances = [
    [logging.getLogger("app"), logging.INFO],
    [logging.getLogger('uvicorn'), logging.INFO],
    [logging.getLogger('azure'), logging.WARNING],
    [logging.getLogger('gunicorn'), logging.INFO],
    [logging.getLogger('asyncpg'), logging.WARNING],
]


middleware = [
    Middleware(ProxyHeadersHostMiddleware),
    Middleware(ProxyHeadersMiddleware, trusted_hosts=Settings.service_domain),
    Middleware(
        TraceRequestMiddleware,
        sampler=AlwaysOnSampler(),
        extra_attrs=dict(
            environment=Settings.ENVIRONMENT,
            server_location=Settings.server_location
        )
    ),
]


async def lifespan(application: Starlette):
    exporter = Exporter(connection_string=Settings.instrumentation_key)
    exporter.add_telemetry_processor(add_cloud_role_name)
    application.state.azure_exporter = exporter

    handler = AzureLogHandler(connection_string=Settings.instrumentation_key)

    handler.add_telemetry_processor(add_cloud_role_name)

    for log, level in logging_instances:
        log.addHandler(handler)
        log.setLevel(level)

    pool = await redis.instantiate_redis_pool()
    application.state.redis = pool

    yield

    pool.close()
    await pool.wait_closed()
    handler.flush()


app = Starlette(
    debug=Settings.DEBUG,
    routes=routes,
    middleware=middleware,
    exception_handlers=exception_handlers,
    lifespan=lifespan
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response: Response = await call_next(request)

    last_modified = datetime.now()
    expires = last_modified + timedelta(minutes=1, seconds=30)

    response.headers['last-modified'] = last_modified.strftime(HTTP_DATE_FORMAT)
    response.headers['expires'] = expires.strftime(HTTP_DATE_FORMAT)

    if response.status_code == 503:
        response.headers['retry-after'] = '300'

    if "cache-control" not in response.headers:
        response.headers['cache-control'] = 'public, must-revalidate, max-age=60, s-maxage=90'

    response.headers['PHE-Server-Loc'] = Settings.server_location

    return response


if __name__ == "__main__":
    from uvicorn import run as uvicorn_run

    uvicorn_run(app, port=1235)
