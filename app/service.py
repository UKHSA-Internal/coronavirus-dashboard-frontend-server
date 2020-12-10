#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import re
import logging
from os import getenv
from datetime import datetime, timedelta
from os.path import abspath, join as join_path, pardir
from typing import Union
from functools import lru_cache

# 3rd party:
from flask import Flask, Response, g, render_template, make_response, request
from flask_minify import minify
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
from app.common.data.variables import NationalAdjectives, IsImproving
from app.common.caching import cache_client
from app.common.utils import get_og_image_names, add_cloud_role_name
from app.database import CosmosDB, Collection
from app.storage import StorageClient
from app.common.data.query_templates import HealthCheck

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
NOT_AVAILABLE = "N/A"
INSTRUMENTATION_CODE = getenv("APPINSIGHTS_INSTRUMENTATIONKEY", "")
AI_INSTRUMENTATION_KEY = f"InstrumentationKey={INSTRUMENTATION_CODE}"
SERVER_LOCATION_KEY = "SERVER_LOCATION"
SERVER_LOCATION = getenv(SERVER_LOCATION_KEY, NOT_AVAILABLE)
PYTHON_TIMESTAMP_LEN = 24
HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"
LOG_LEVEL = getenv("LOG_LEVEL", "INFO")

timestamp_pattern = "%A %d %B %Y at %I:%M %p"
timezone_LN = timezone("Europe/London")

instance_path = abspath(join_path(abspath(__file__), pardir))

app = Flask(
    __name__,
    instance_path=instance_path,
    static_folder="static",
    static_url_path="/assets",
    template_folder='templates'
)

config_integration.trace_integrations(['requests'])
config_integration.trace_integrations(['logging'])

exporter = AzureExporter(connection_string=AI_INSTRUMENTATION_KEY)
exporter.add_telemetry_processor(add_cloud_role_name)

middleware = FlaskMiddleware(
    app=app,
    exporter=exporter,
    sampler=AlwaysOnSampler(),
    propagator=TraceContextPropagator()
)

app.config.from_object('app.config.Config')

# Logging -------------------------------------------------
log_level = getattr(logging, LOG_LEVEL)

logging_instances = [
    [app.logger, log_level],
    [logging.getLogger('werkzeug'), log_level],
    [logging.getLogger('azure'), logging.WARNING],
    [logging.getLogger('homepage_server'), log_level],
]

# ---------------------------------------------------------

app.register_blueprint(home_page)
app.register_blueprint(postcode_page)

cache_client.init_app(app)

minifier = minify(
    html=True,
    js=True,
    cssless=True,
    caching_limit=0,
    fail_safe=True
)


@app.template_filter()
@lru_cache(maxsize=256)
def format_timestamp(latest_timestamp: str) -> str:
    ts_python_iso = latest_timestamp[:-1] + "+00:00"
    ts = datetime.fromisoformat(ts_python_iso)
    ts_london = ts.astimezone(timezone_LN)
    formatted = ts_london.strftime(timestamp_pattern)
    result = re.sub(r'\s([AP]M)', lambda found: found.group(1).lower(), formatted)
    return result


@app.template_filter()
@lru_cache(maxsize=64)
def as_datestamp(latest_timestamp: str) -> str:
    datestamp = latest_timestamp.split("T")[0]
    return datestamp


@app.context_processor
def is_improving():
    def inner(metric, value):
        if value == 0:
            return None

        improving = IsImproving[metric](value)
        if isinstance(improving, bool):
            return improving
        # if improving != 0 and value != 0:
        #     return improving
        return None
    return dict(is_improving=inner)


@app.template_filter()
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


@app.template_filter()
def isnone(value):
    return value is None


@app.errorhandler(404)
def handle_404(err):
    app.logger.info(f"HTTP 404 response on <{request.url}>")
    return render_template("errors/404.html"), 404


@app.errorhandler(Exception)
def handle_500(err):
    additional_info = {
        'website_timestamp': g.website_timestamp,
        'latest_release': g.timestamp,
        'db_host': getenv("AzureCosmosHost", NOT_AVAILABLE),
        "API_environment": getenv("API_ENV", NOT_AVAILABLE),
        "server_location": getenv("SERVER_LOCATION", NOT_AVAILABLE),
        "is_dev": getenv("IS_DEV", NOT_AVAILABLE),
        "redis": getenv("AZURE_REDIS_HOST", NOT_AVAILABLE),
        "AzureCosmosDBName": getenv("AzureCosmosDBName", NOT_AVAILABLE),
        "AzureCosmosCollection": getenv("AzureCosmosCollection", NOT_AVAILABLE),
        "AzureCosmosDestinationsCollection": getenv(
            "AzureCosmosDestinationsCollection",
            NOT_AVAILABLE
        ),
    }

    app.logger.exception(err, extra={'custom_dimensions': additional_info})

    return render_template("errors/500.html"), 500


@app.context_processor
def inject_globals():
    return dict(
        DEBUG=app.debug,
        national_adjectives=NationalAdjectives,
        timestamp=g.website_timestamp,
        app_insight_token=INSTRUMENTATION_CODE,
        og_images=get_og_image_names(g.timestamp)
    )


@app.before_request
def prepare_context():
    handler = AzureLogHandler(connection_string=AI_INSTRUMENTATION_KEY)
    handler.add_telemetry_processor(add_cloud_role_name)

    for log, level in logging_instances:
        log.addHandler(handler)
        log.setLevel(level)

    g.data_db = CosmosDB(Collection.DATA)
    g.lookup_db = CosmosDB(Collection.LOOKUP)
    g.weekly_db = CosmosDB(Collection.WEEKLY)

    with StorageClient(**WEBSITE_TIMESTAMP) as client:
        g.website_timestamp = client.download().readall().decode()

    with StorageClient(**LATEST_PUBLISHED_TIMESTAMP) as client:
        g.timestamp = client.download().readall().decode()

    g.log_handler = handler

    return None


@app.teardown_appcontext
def teardown_db(exception):
    g.log_handler.flush()

    db_instances = [
        g.pop('data_db', None),
        g.pop('lookup_db', None),
        g.pop('weekly_db', None),
    ]

    for db in db_instances:
        if db is not None:
            db.close()


@app.after_request
def prepare_response(resp: Response):
    last_modified = datetime.strptime(
        g.timestamp[:PYTHON_TIMESTAMP_LEN] + "Z",
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    expires = datetime.now() + timedelta(minutes=1, seconds=30)

    resp.headers['Last-Modified'] = last_modified.strftime(HTTP_DATE_FORMAT)
    resp.headers['Expires'] = expires.strftime(HTTP_DATE_FORMAT)
    resp.headers['PHE-Server-Loc'] = SERVER_LOCATION

    try:
        minified = [minifier.get_minified(item.decode(), 'html') for item in resp.response]
        data = str.join("", minified).encode()
        resp.set_data(data)
    except UnicodeDecodeError as e:
        app.logger.warning(e)

    return resp


@app.route("/healthcheck", methods=("HEAD", "GET"))
def health_check(**kwargs):
    result = g.lookup_db.query(HealthCheck, params=list()).pop()

    if len(result) > 0:
        return make_response("ALIVE", 200)

    raise RuntimeError("Health check failed.")


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False, port=5050)
