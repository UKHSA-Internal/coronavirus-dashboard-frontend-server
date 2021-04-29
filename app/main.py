#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 3rd party:
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.requests import Request

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from opencensus.trace.samplers import AlwaysOnSampler
from starlette.responses import FileResponse, Response

# Internal:
from app.postcode.views import postcode_page
from app.landing.views import home_page
from app.healthcheck.views import run_healthcheck
from app.config import Settings
from app.common.utils import add_cloud_role_name
from app.middleware.tracers.starlette import TraceRequestMiddleware
from app.middleware.headers import ProxyHeadersHostMiddleware
from app.exceptions import exception_handlers
from app import generic
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'app'
]


HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


assets_path = Path(__file__).parent.joinpath("assets")

routes = [
    Route('/', endpoint=home_page, methods=["GET"]),
    Route(f'/{Settings.healthcheck_path}', endpoint=run_healthcheck, methods=["GET", "HEAD"]),
    Route('/search', endpoint=postcode_page, methods=["GET"]),
    Mount('/assets', StaticFiles(directory=assets_path.resolve()), name="static"),
    Route('/favicon.ico', endpoint=generic.favicon_ico),
    Route('/favicon.png', endpoint=generic.favicon_png),
    Route('/sitemap.xml', endpoint=generic.sitemap),
]


logging_instances = [
    [logging.getLogger("app"), logging.INFO],
    [logging.getLogger('uvicorn'), logging.WARNING],
    [logging.getLogger('uvicorn.access'), logging.WARNING],
    [logging.getLogger('uvicorn.error'), logging.ERROR],
    [logging.getLogger('azure'), logging.WARNING],
    [logging.getLogger('gunicorn'), logging.WARNING],
    [logging.getLogger('gunicorn.access'), logging.WARNING],
    [logging.getLogger('gunicorn.error'), logging.ERROR],
    [logging.getLogger('asyncpg'), logging.WARNING],
]


middleware = [
    Middleware(ProxyHeadersHostMiddleware),
    Middleware(ProxyHeadersMiddleware, trusted_hosts=Settings.service_domain),
    Middleware(
        TraceRequestMiddleware,
        sampler=AlwaysOnSampler(),
        instrumentation_key=Settings.instrumentation_key,
        cloud_role_name=add_cloud_role_name,
        extra_attrs=dict(
            environment=Settings.ENVIRONMENT,
            server_location=Settings.server_location
        ),
        logging_instances=logging_instances
    ),
]


app = Starlette(
    debug=Settings.DEBUG,
    routes=routes,
    middleware=middleware,
    exception_handlers=exception_handlers,
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)

    last_modified = datetime.now()
    expires = last_modified + timedelta(minutes=1, seconds=30)

    response.headers['last-modified'] = last_modified.strftime(HTTP_DATE_FORMAT)
    response.headers['expires'] = expires.strftime(HTTP_DATE_FORMAT)

    if "cache-control" not in response.headers:
        response.headers['cache-control'] = 'public, must-revalidate, max-age=30, s-maxage=90'

    response.headers['PHE-Server-Loc'] = Settings.server_location

    return response


if __name__ == "__main__":
    from uvicorn import run as uvicorn_run

    uvicorn_run(app, port=1235)
