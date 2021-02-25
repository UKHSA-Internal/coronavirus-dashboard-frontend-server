#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import re
from os import getenv
from datetime import datetime
from os.path import abspath, join as join_path, pardir
from typing import Union
from functools import lru_cache

# 3rd party:
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# from flask_minify import minify
from pytz import timezone

from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.trace.samplers import AlwaysOnSampler
from opencensus.trace import config_integration
from opencensus.trace.propagation.trace_context_http_header_format import TraceContextPropagator

# Internal:
from app.postcode.views import postcode_page
from app.landing.views import home_page
from app.healthcheck.view import healthcheck
from app.common.data.variables import NationalAdjectives, IsImproving
from app.config import Settings
# from app.common.caching import cache_client
# from app.common.banner import get_banners
# from app.common.whats_new import get_whats_new_banners
# from app.common.utils import get_og_image_names, add_cloud_role_name, get_notification_content
# from app.storage import StorageClient
# from app.common.data.query_templates import HealthCheck
# from app.common.exceptions import HandledException
# from app.database import CosmosDB, Collection

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'app'
]


HEALTHCHECK_PATH = "/healthcheck"
WEBSITE_TIMESTAMP = {
    "container": "publicdata",
    "path":  "assets/dispatch/website_timestamp"
}
LATEST_PUBLISHED_TIMESTAMP = {
    "container": "pipeline",
    "path": "info/latest_published"
}
NOT_AVAILABLE = "N/A"
INSTRUMENTATION_CODE = getenv("APPINSIGHTS_INSTRUMENTATIONKEY", "")
AI_INSTRUMENTATION_KEY = f"InstrumentationKey={INSTRUMENTATION_CODE}"
SERVER_LOCATION_KEY = "SERVER_LOCATION"
DOMAIN_NAME_KEY = 'URL_LOCATION'
SERVICE_DOMAIN = getenv(DOMAIN_NAME_KEY, str())
SERVER_LOCATION = getenv(SERVER_LOCATION_KEY, NOT_AVAILABLE)
PYTHON_TIMESTAMP_LEN = 24
HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
LOG_LEVEL = getenv("LOG_LEVEL", "INFO")

timestamp_pattern = "%A %d %B %Y at %-I:%M %p"
timezone_LN = timezone("Europe/London")

instance_path = abspath(join_path(abspath(__file__), pardir))


routes = [
    Route('/', endpoint=home_page, methods=["GET"]),
    Route(HEALTHCHECK_PATH, endpoint=healthcheck, methods=["GET", "HEAD"]),
    Route('/search', endpoint=postcode_page, methods=["GET"]),
    Mount("/assets", StaticFiles(directory="static"), name="static")
]

middleware = [
    Middleware(ProxyHeadersMiddleware, trusted_hosts=SERVICE_DOMAIN)
]

app = Starlette(debug=Settings.DEBUG, routes=routes, middleware=middleware)


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
# log_level = getattr(logging, LOG_LEVEL)
#
# logging_instances = [
#     [app.logger, log_level],
#     [logging.getLogger('werkzeug'), logging.WARNING],
#     [logging.getLogger('azure'), logging.WARNING]
# ]

# ---------------------------------------------------------
#
# app.register_blueprint(home_page)
# app.register_blueprint(postcode_page)
#
# cache_client.init_app(app)
#
# minifier = minify(
#     html=True,
#     js=True,
#     cssless=True,
#     caching_limit=0,
#     fail_safe=True
# )


# @app.template_filter()
@lru_cache(maxsize=256)
def format_timestamp(latest_timestamp: str) -> str:
    ts_python_iso = latest_timestamp[:-1] + "+00:00"
    ts = datetime.fromisoformat(ts_python_iso)
    ts_london = ts.astimezone(timezone_LN)
    formatted = ts_london.strftime(timestamp_pattern)
    result = re.sub(r'\s([AP]M)', lambda found: found.group(1).lower(), formatted)
    return result


# @app.template_filter()
@lru_cache(maxsize=64)
def as_datestamp(latest_timestamp: str) -> str:
    datestamp = latest_timestamp.split("T")[0]
    return datestamp


# @app.context_processor
def is_improving(metric, value):
    if value == 0:
        return None

    improving = IsImproving[metric](value)
    if isinstance(improving, bool):
        return improving
    # if improving != 0 and value != 0:
    #     return improving
    return None


# @app.template_filter()
@lru_cache(maxsize=256)
def format_number(value: Union[int, float]) -> str:
    try:
        value_int = int(value)
    except ValueError:
        if value == "0-2":
            value = "0 &ndash; 2"
        return str(value)
    except TypeError:
        return NOT_AVAILABLE

    if value == value_int:
        return format(value_int, ',d')

    return str(value)


# @app.template_filter()
def trim_area_name(area_name):
    pattern = re.compile(r"(nhs\b.*)", re.IGNORECASE)
    name = pattern.sub("", area_name)

    return name.strip()


# @app.template_filter()
def cards_to_easy_read(cards):
    cards_dict = {
        item["caption"].lower(): item
        for item in cards
    }

    return cards_dict


# @app.template_filter()
def pluralise(number, singular, plural, null=str()):
    if abs(number) > 1:
        return plural

    if abs(number) == 1:
        return singular

    if number == 0 and not len(null) :
        return plural

    return null


# @app.template_filter()
# def comparison_verb(number, greater, smaller, same):
#     if number > 0:
#         return greater
#
#     if number < 0:
#         return smaller
#
#     return same


# @app.template_filter()
# def isnone(value):
#     return value is None


# @app.errorhandler(404)
# def handle_404(err):
#     if isinstance(err, HandledException):
#         return err
#
#     app.logger.info(f"404 - Not found", extra={'custom_dimensions': {"url": request.url}})
#     return render_template("errors/404.html"), 404


# @app.errorhandler(Exception)
# def handle_500(err):
#     if isinstance(err, HandledException):
#         return err
#
#     additional_info = {
#         'website_timestamp': g.website_timestamp,
#         'latest_release': g.timestamp,
#         'db_host': getenv("AzureCosmosHost", NOT_AVAILABLE),
#         "API_environment": getenv("API_ENV", NOT_AVAILABLE),
#         "server_location": getenv("SERVER_LOCATION", NOT_AVAILABLE),
#         "is_dev": getenv("IS_DEV", NOT_AVAILABLE),
#         "redis": getenv("AZURE_REDIS_HOST", NOT_AVAILABLE),
#         "AzureCosmosDBName": getenv("AzureCosmosDBName", NOT_AVAILABLE),
#         "AzureCosmosCollection": getenv("AzureCosmosCollection", NOT_AVAILABLE),
#         "AzureCosmosDestinationsCollection": getenv(
#             "AzureCosmosDestinationsCollection",
#             NOT_AVAILABLE
#         ),
#     }
#
#     app.logger.exception(err, extra={'custom_dimensions': additional_info})
#
#     return render_template("errors/500.html"), 500


# @cache_client.memoize(timeout=120)
# def get_globals(website_timestamp):
#     response = dict(
#         DEBUG=app.debug,
#         changelog=get_notification_content(website_timestamp),
#         national_adjectives=NationalAdjectives,
#         timestamp=website_timestamp,
#         app_insight_token=INSTRUMENTATION_CODE,
#         og_images=get_og_image_names(g.timestamp),
#         banners=get_banners,
#         whatsnew_banners=get_whats_new_banners
#     )
#
#     return response


# @app.context_processor
# def inject_globals():
#     if request.method == "HEAD":
#         return dict()
#
#     return get_globals(g.website_timestamp)


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


# @app.teardown_appcontext
# def teardown_db(exception):
#     # db_instances = [
#     #     g.pop('data_db', None),
#     #     g.pop('lookup_db', None),
#     #     g.pop('weekly_db', None),
#     # ]
#     #
#     # for db in db_instances:
#     #     if db is not None:
#     #         db.close()


# @app.after_request
# def prepare_response(resp: Response):
#     last_modified = datetime.now()
#     # (
#     #     g.timestamp[:PYTHON_TIMESTAMP_LEN] + "Z",
#     #     "%Y-%m-%dT%H:%M:%S.%fZ"
#     # )
#
#     resp.last_modified = last_modified
#     resp.expires = datetime.now() + timedelta(minutes=1, seconds=30)
#     resp.cache_control.max_age = 30
#     resp.cache_control.public = True
#     resp.cache_control.s_maxage = 90
#     resp.cache_control.must_revalidate = True
#     resp.headers['PHE-Server-Loc'] = SERVER_LOCATION
#
#     try:
#         minified = [minifier.get_minified(item.decode(), 'html') for item in resp.response]
#         data = str.join("", minified).encode()
#         resp.set_data(data)
#     except UnicodeDecodeError as e:
#         app.logger.warning(e)
#
#     # g.log_handler.flush()
#
#     return resp


# @app.middleware("http")
# async def add_process_time_header(request: Request, call_next):
#     # with StorageClient(**WEBSITE_TIMESTAMP) as client:
#     #     website_timestamp = client.download().readall().decode()
#
#     # with StorageClient(**LATEST_PUBLISHED_TIMESTAMP) as client:
#     #     timestamp = client.download().readall().decode()
#
#     # initial_g = SimpleNamespace()
#     # requestvars.request_global.set(initial_g)
#     # requestvars.g().timestmap = timestamp,
#     # requestvars.g().website_timestamp = website_timestamp
#     response = await call_next(request)
#     return response



if __name__ == "__main__":
    from uvicorn import run as uvicorn_run

    uvicorn_run(app, port=1234)
