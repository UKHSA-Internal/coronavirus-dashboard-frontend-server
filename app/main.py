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

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from opencensus.trace.samplers import AlwaysOnSampler

# Internal:
from app.postcode.views import postcode_page
from app.landing.views import home_page
from app.healthcheck.views import run_healthcheck
from app.exceptions.views import exception_handlers
from app.config import Settings
from app.common.utils import add_cloud_role_name
from app.middleware.tracers import TraceHeaderMiddleware

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'app'
]


WEBSITE_TIMESTAMP = {
    "container": "publicdata",
    "path":  "assets/dispatch/website_timestamp"
}
LATEST_PUBLISHED_TIMESTAMP = {
    "container": "pipeline",
    "path": "info/latest_published"
}

HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

routes = [
    Route('/', endpoint=home_page, methods=["GET"]),
    Route('/heathcheck', endpoint=run_healthcheck, methods=["GET", "HEAD"]),
    Route('/search', endpoint=postcode_page, methods=["GET"]),
    Mount('/assets', StaticFiles(directory="static"), name="static")
]

logging_instances = [
    [logging.getLogger('landing_page'), logging.INFO],
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
    Middleware(ProxyHeadersMiddleware, trusted_hosts=Settings.service_domain),
    Middleware(
        TraceHeaderMiddleware,
        sampler=AlwaysOnSampler(),
        instrumentation_key=Settings.instrumentation_key,
        cloud_role_name=add_cloud_role_name,
        extra_attrs=dict(
            environment=Settings.ENVIRONMENT,
            server_location=Settings.server_location
        ),
        logging_instances=logging_instances
    )
]


app = Starlette(
    debug=Settings.DEBUG,
    routes=routes,
    middleware=middleware,
    exception_handlers=exception_handlers,
)


# app.include_router(home_page, default_response_class=HTMLResponse)
# app.include_router(postcode_page, default_response_class=HTMLResponse)
#
#     # instance_path=instance_path,
#     static_folder="static",
#     static_url_path="/assets",
#     template_folder='templates'
# )
# app.url_map.strict_slashes = False
# config_integration.trace_integrations(['requests'])
# config_integration.trace_integrations(['logging'])

# app.config.from_object('app.config.Config')

# Logging -------------------------------------------------
# log_level = getattr(logging, Settings.log_level)
#
# logging_instances = [
#     [app.logger, log_level],
#     [logging.getLogger('werkzeug'), logging.WARNING],
#     [logging.getLogger('azure'), logging.WARNING]
# ]

# ---------------------------------------------------------


# @app.template_filter()
# def pluralise(number, singular, plural, null=str()):
#     if abs(number) > 1:
#         return plural
#
#     if abs(number) == 1:
#         return singular
#
#     if number == 0 and not len(null):
#         return plural
#
#     return null


# @app.template_filter()
# def isnone(value):
#     return value is None


# @app.before_first_request
# def prep_service():
#     exporter = AzureExporter(connection_string=AI_INSTRUMENTATION_KEY)
#     exporter.add_telemetry_processor(add_cloud_role_name)
#
#     _ = FlaskMiddleware(
#         app=app,
#         exporter=exporter,
#         sampler=AlwaysOnSampler(),
#         propagator=TraceContextPropagator()
#     )
#
#     handler = AzureLogHandler(connection_string=AI_INSTRUMENTATION_KEY)
#
#     handler.add_telemetry_processor(add_cloud_role_name)
#
#     for log, level in logging_instances:
#         log.addHandler(handler)
#         log.setLevel(level)


# @app.before_request
# def prepare_context():
#     custom_dims = dict(
#         custom_dimensions=dict(
#             is_healthcheck=request.path == HEALTHCHECK_PATH,
#             url=str(request.url),
#             path=str(request.path),
#             query_string=str(request.query_string)
#         )
#     )
#
#     app.logger.info(request.url, extra=custom_dims)
#
#     with StorageClient(**WEBSITE_TIMESTAMP) as client:
#         g.website_timestamp = client.download().readall().decode()
#
#     with StorageClient(**LATEST_PUBLISHED_TIMESTAMP) as client:
#         g.timestamp = client.download().readall().decode()
#
#     return None


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)

    last_modified = datetime.now()
    expires = last_modified + timedelta(minutes=1, seconds=30)

    response.headers['last-modified'] = last_modified.strftime(HTTP_DATE_FORMAT)
    response.headers['expires'] = expires.strftime(HTTP_DATE_FORMAT)
    response.headers['cache-control'] = 'public, must-revalidate, max-age=30, s-maxage=90'
    response.headers['PHE-Server-Loc'] = Settings.server_location

    return response


# @app.middleware("http")
# async def logging_middleware(request: Request, call_next):
#     exporter = AzureExporter(connection_string=Settings.instrumentation_key)
#     exporter.add_telemetry_processor(add_cloud_role_name)
#
#     tracer = Tracer(
#         exporter=exporter,
#         sampler=AlwaysOnSampler()
#     )
#
#     with tracer.span("main") as span:
#         span.span_kind = SpanKind.SERVER
#
#         response = await call_next(request)
#
#         tracer.add_attribute_to_current_span(
#             attribute_key=HTTP_STATUS_CODE,
#             attribute_value=response.status_code
#         )
#
#         tracer.add_attribute_to_current_span(
#             attribute_key=HTTP_URL,
#             attribute_value=str(request.url)
#         )
#
#         tracer.add_attribute_to_current_span("environment", Settings.ENVIRONMENT)
#         tracer.add_attribute_to_current_span("server_location", Settings.server_location)
#
#     return response


if __name__ == "__main__":
    from uvicorn import run as uvicorn_run

    uvicorn_run(app, port=1234)
