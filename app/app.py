#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
import re
from datetime import datetime, timedelta
from gzip import compress
from os.path import abspath, join as join_path, pardir
from os import getenv
from typing import Union
from functools import lru_cache

# 3rd party:
from flask import Flask, request, Response, g, appcontext_pushed
from contextlib import contextmanager
from flask import Flask, request, Response, g, render_template
from azure.functions import HttpRequest, HttpResponse, WsgiMiddleware, Context
from flask_minify import minify
from pytz import timezone

# Internal:
from .postcode.views import postcode_page
from .landing.views import home_page

from .common.caching import cache_client
from .common.utils import get_og_image_names

try:
    from __app__.database import CosmosDB, Collection
    from __app__.storage import StorageClient
except ImportError:
    from database import CosmosDB, Collection
    from storage import StorageClient

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'main',
    'app',
    'inject_timestamps_tests'
]


STORAGE_CONN_STR = getenv("StaticFrontendStorage")

with StorageClient("$web", f"static/css/", connection_string=STORAGE_CONN_STR) as client:
    css_names = [item["name"] for item in client if item["name"].endswith(".css")]


timestamp: str = str()
website_timestamp: str = str()
timestamp_pattern = "%A %d %B %Y at %I:%M %p"
timezone_LN = timezone("Europe/London")


instance_path = abspath(join_path(abspath(__file__), pardir))

app = Flask(__name__, instance_path=instance_path)

try:
    app.config.from_object('__app__.app.config.Config')
except ImportError:
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


@app.template_filter()
@lru_cache(maxsize=256)
def format_number(value: Union[int, float]) -> str:
    try:
        value_int = int(value)
    except ValueError:
        if value == "0-2":
            value = "0 &ndash; 2"
        return str(value)

    if value == value_int:
        return format(value_int, ',d')

    return str(value)


@contextmanager
def inject_timestamps_tests(app, timestamp, website_timestamp):
    def handler(sender, **kwargs):
        g.timestamp = timestamp
        g.website_timestamp = website_timestamp
        g.testing = True
    with appcontext_pushed.connected_to(handler, app):
        yield
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
        timestamp=g.website_timestamp,
        og_images=get_og_image_names(g.timestamp),
        styles=css_names
    )


@app.before_request
def inject_timestamps():
    global timestamp, website_timestamp, testing

    # currently need to comment these two out for testing to work
    
    # g.timestamp = timestamp
    # g.website_timestamp = website_timestamp

    g.data_db = CosmosDB(Collection.DATA)
    g.lookup_db = CosmosDB(Collection.LOOKUP)
    g.weekly_db = CosmosDB(Collection.WEEKLY)

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
        g.timestamp[:24] + "Z",
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    expires = datetime.now() + timedelta(minutes=1, seconds=30)

    resp.headers['Last-Modified'] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
    resp.headers['Expires'] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    minified = [minifier.get_minified(item.decode(), 'html') for item in resp.response]
    data = str.join("", minified).encode()

    accept_encoding = request.headers.get("Accept-Encoding", "")

    if 'gzip' in accept_encoding:
        data = compress(data)
        resp.headers['Content-Encoding'] = "gzip"

    resp.set_data(data)
    return resp


def main(req: HttpRequest, context: Context, latestPublished: str,
         websiteTimestamp: str) -> HttpResponse:
    global timestamp, website_timestamp
    timestamp = latestPublished
    website_timestamp = websiteTimestamp
    logging.info(timestamp)
    try:
        application = WsgiMiddleware(app.wsgi_app)
        return application.main(req, context)
    except Exception as err:
        logging.exception(err)
