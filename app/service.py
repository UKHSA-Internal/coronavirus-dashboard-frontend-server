#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
import re
from os import getenv
from datetime import datetime, timedelta
from os.path import abspath, join as join_path, pardir
from typing import Union
from functools import lru_cache

# 3rd party:
from flask import Flask, Response, g, render_template, make_response
from flask_minify import minify
from pytz import timezone

# Internal:
from app.postcode.views import postcode_page
from app.landing.views import home_page
from app.common.data.variables import NationalAdjectives, IsImproving
from app.common.caching import cache_client
from app.common.utils import get_og_image_names

from database import CosmosDB, Collection
from storage import StorageClient

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
APP_INSIGHT_KEY = "APPINSIGHTS_INSTRUMENTATIONKEY"
SERVER_LOCATION_KEY = "SERVER_LOCATION"
SERVER_LOCATION = getenv(SERVER_LOCATION_KEY, NOT_AVAILABLE)
PYTHON_TIMESTAMP_LEN = 24
HTTP_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"

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

app.config.from_object('app.config.Config')


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
        improving = IsImproving[metric](value)
        if improving != 0 and value != 0:
            return improving
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
def handle_404(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(Exception)
def handle_500(e):
    logging.exception(e)
    return render_template("errors/500.html"), 500


@app.context_processor
def inject_globals():
    return dict(
        DEBUG=app.debug,
        national_adjectives=NationalAdjectives,
        timestamp=g.website_timestamp,
        app_insight_token=getenv(APP_INSIGHT_KEY, ""),
        og_images=get_og_image_names(g.timestamp)
    )


@app.before_request
def inject_timestamps():
    g.data_db = CosmosDB(Collection.DATA)
    g.lookup_db = CosmosDB(Collection.LOOKUP)
    g.weekly_db = CosmosDB(Collection.WEEKLY)

    with StorageClient(**WEBSITE_TIMESTAMP) as client:
        g.website_timestamp = client.download().readall().decode()

    with StorageClient(**LATEST_PUBLISHED_TIMESTAMP) as client:
        g.timestamp = client.download().readall().decode()

    return None


@app.teardown_appcontext
def teardown_db(exception):
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

    minified = [minifier.get_minified(item.decode(), 'html') for item in resp.response]
    data = str.join("", minified).encode()

    resp.set_data(data)
    return resp


@app.route("/healthcheck", methods=("HEAD", "GET"))
def health_check(**kwargs):
    from .common.data.query_templates import HealthCheck
    result = g.data_db.query(HealthCheck, params=list()).pop()

    if result.endswith("Z"):
        return make_response("", 200)

    raise make_response("", 500)


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False, port=5050)
