#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from datetime import datetime, timedelta

# 3rd party:
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.requests import Request


from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.trace.samplers import AlwaysOnSampler
from opencensus.trace import config_integration
from opencensus.trace.propagation.trace_context_http_header_format import TraceContextPropagator

# Internal:
from app.postcode.views import postcode_page
from app.landing.views import home_page
from app.healthcheck.views import healthcheck
from app.exceptions.views import exception_handlers
from app.config import Settings

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

AI_INSTRUMENTATION_KEY = f"InstrumentationKey={Settings.instrumentation_key}"

HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

routes = [
    Route('/', endpoint=home_page, methods=["GET"]),
    Route('/heathcheck', endpoint=healthcheck, methods=["GET", "HEAD"]),
    Route('/search', endpoint=postcode_page, methods=["GET"]),
    Mount('/assets', StaticFiles(directory="static"), name="static")
]

middleware = [
    Middleware(ProxyHeadersMiddleware, trusted_hosts=Settings.service_domain)
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
def pluralise(number, singular, plural, null=str()):
    if abs(number) > 1:
        return plural

    if abs(number) == 1:
        return singular

    if number == 0 and not len(null):
        return plural

    return null


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


if __name__ == "__main__":
    from uvicorn import run as uvicorn_run

    uvicorn_run(app, port=1234)
