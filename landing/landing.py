#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
import re
from operator import itemgetter
from datetime import datetime, timedelta
from gzip import compress
from os.path import abspath, join as join_path, pardir
from os import getenv
from typing import List, Dict, Union

# 3rd party:
from flask import Flask, render_template, request, Response
from azure.functions import (
    HttpRequest, HttpResponse, WsgiMiddleware,
    Context
)
from flask_minify import minify
from pytz import timezone

# Internal:
from .visualisation import plot_thumbnail, get_colour
from .data.queries import (
    get_last_fortnight, get_data_by_postcode,
    get_msoa_data, get_r_values, get_alert_level,
    get_postcode_areas, latest_rate_by_metric
)
from .caching import cache_client

try:
    from __app__.database import CosmosDB
    from __app__.storage import StorageClient
except ImportError:
    from database import CosmosDB
    from storage import StorageClient

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'main'
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

app.config.from_object('__app__.landing.config.Config')

cache_client.init_app(app)

minifier = minify(
    html=True,
    js=True,
    cssless=True,
    caching_limit=0,
    fail_safe=True
)

postcode_pattern = re.compile(r'(^[a-z]{1,2}\d{1,2}[a-z]?\s?\d{1,2}[a-z]{1,2}$)', re.I)

get_value = itemgetter("value")
get_area_type = itemgetter("areaType")

main_metric_names: List[str] = [
    "newCasesByPublishDate",
    "newDeaths28DaysByPublishDate",
    "newAdmissions",
    "newPCRTestsByPublishDate",
]


@app.template_filter()
def format_timestamp(latest_timestamp: str) -> str:
    ts_python_iso = latest_timestamp[:-1] + "+00:00"
    ts = datetime.fromisoformat(ts_python_iso)
    ts_london = ts.astimezone(timezone_LN)
    formatted = ts_london.strftime(timestamp_pattern)
    result = re.sub(r'\s([AP]M)', lambda found: found.group(1).lower(), formatted)
    return result


@cache_client.memoize(60 * 60 * 6)
def get_og_image_names(latest_timestamp: str) -> list:
    ts_python_iso = latest_timestamp[:-2]
    ts = datetime.fromisoformat(ts_python_iso)
    date = ts.strftime("%Y%m%d")
    og_names = [
        f"/downloads/og-images/og-{metric}_{date}.png"
        for metric in main_metric_names
    ]

    og_names.insert(0, f"/downloads/og-images/og-summary_{date}.png")

    return og_names


@app.template_filter()
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


def get_change(metric_data):
    sigma_this_week = sum(map(get_value, metric_data[:7]))
    sigma_last_week = sum(map(get_value, metric_data[7:14]))
    delta = sigma_this_week - sigma_last_week

    delta_percentage = (sigma_this_week / max(sigma_last_week, 0.5) - 1) * 100

    if delta_percentage > 0:
        trend = 0
    elif delta_percentage < 0:
        trend = 180
    else:
        trend = 90

    return {
        "percentage": format(delta_percentage, ".1f"),
        "value": int(round(delta)),
        "total": sigma_this_week,
        "trend": trend
    }


def get_card_data(metric_name: str, metric_data, graph=True):
    change = get_change(metric_data)
    colour = get_colour(change, metric_name)

    response = {
        "data": metric_data,
        "change": change,
        "colour": colour,
        "latest_date": metric_data[0]["date"].strftime('%-d %B')
    }

    if graph:
        response["graph"] = plot_thumbnail(metric_data, change, metric_name)

    return response


@cache_client.memoize(60 * 60 * 6)
def get_fortnight_data(latest_timestamp: str, area_name: str = "United Kingdom") -> Dict[str, dict]:
    result = dict()

    for name in main_metric_names:
        metric_data = get_last_fortnight(latest_timestamp, area_name, name)
        result[name] = get_card_data(name, metric_data)

    return result


@cache_client.memoize(60 * 60 * 6)
def get_main_data(latest_timestamp: str):
    # ToDo: Integrate this with postcode data.
    data = get_fortnight_data(latest_timestamp)

    result = dict(
        cards=[
            {
                "caption": "Cases",
                "heading": "People tested positive",
                **data['newCasesByPublishDate'],
                "data": data['newCasesByPublishDate']['data'],
            },
            {
                "caption": "Deaths",
                "heading": "Deaths within 28 days of positive test",
                **data['newDeaths28DaysByPublishDate'],
                "data": data['newDeaths28DaysByPublishDate']['data'],

            },
            {
                "caption": "Healthcare",
                "heading": "Patients admitted",
                **data['newAdmissions'],
                "data": data['newAdmissions']['data'],
            },
            {
                "caption": "Testing",
                "heading": "Virus tests processed",
                **data['newPCRTestsByPublishDate'],
                "data": data['newPCRTestsByPublishDate']['data'],
            },
        ] 
    )

    return result


def get_by_smallest_areatype(items, areatype_getter):
    order = [
        "lsoa",
        "msoa",
        "ltla",
        "utla",
        "region",
        "nhsRegion",
        "nation",
        "overview"
    ]
    area_types = map(areatype_getter, items)

    min_index = len(order) - 1
    result = None

    for item_ind, area_type in enumerate(area_types):
        order_index = order.index(area_type)
        if area_type in order and order_index < min_index:
            result = items[item_ind]
            min_index = order_index

    return result


@app.context_processor
def inject_debug():
    return dict(DEBUG=app.debug)


@app.after_request
def prepare_response(resp: Response):
    global timestamp

    last_modified = datetime.strptime(
        timestamp[:24] + "Z",
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


@cache_client.memoize(60 * 60 * 6)
def get_validated_postcode(params):
    found = postcode_pattern.search(params.get("postcode", "").strip())

    if found is not None:
        extract = found.group(0)
        return extract

    return None


@app.route('/search', methods=['GET'])
def postcode_search() -> render_template:
    global timestamp, website_timestamp

    postcode = get_validated_postcode(request.args)

    data = get_main_data(timestamp)

    if postcode is None:
        return render_template(
            "main.html",
            og_images=get_og_image_names(timestamp),
            invalid_postcode=True,
            styles=css_names,
            r_values=get_r_values(timestamp),
            cases_rate=latest_rate_by_metric(timestamp, "newCasesBySpecimenDate"),
            deaths_rate=latest_rate_by_metric(timestamp, "newDeaths28DaysByDeathDate"),
            timestamp=website_timestamp,
            **data
        )

    try:
        response = {
            category: {
                **values,
                **get_card_data(values["metric"], values['data'], False)
            }
            for category, values in get_data_by_postcode(postcode, timestamp).items()
        }
    except IndexError as err:
        logging.exception(err)
        return render_template(
            "main.html",
            og_images=get_og_image_names(timestamp),
            styles=css_names,
            invalid_postcode=True,
            r_values=get_r_values(timestamp),
            cases_rate=latest_rate_by_metric(timestamp, "newCasesBySpecimenDate"),
            deaths_rate=latest_rate_by_metric(timestamp, "newDeaths28DaysByDeathDate"),
            timestamp=website_timestamp,
            **data
        )

    postcode_data = get_postcode_areas(postcode).pop()

    healthcare_region = postcode_data['nhsRegionName']
    if healthcare_region is None:
        healthcare_region = postcode_data['nationName']

    return render_template(
        "postcode_results.html",
        og_images=get_og_image_names(timestamp),
        styles=css_names,
        postcode_data=response,
        postcode=postcode.upper(),
        area_info=get_postcode_areas(postcode)[0],
        cases_rate=latest_rate_by_metric(timestamp, "newCasesBySpecimenDate", True, postcode),
        timestamp=website_timestamp,
        r_values=get_r_values(timestamp, healthcare_region),
        smallest_area=get_by_smallest_areatype(list(response.values()), get_area_type),
        alert_level=get_alert_level(postcode, timestamp),
        msoa=get_msoa_data(postcode, timestamp),
        **data
    )


@app.route('/', methods=['GET'])
@cache_client.cached(timeout=120)
def index() -> render_template:
    global timestamp, website_timestamp

    data = get_main_data(timestamp)
    return render_template(
        "main.html",
        og_images=get_og_image_names(timestamp),
        styles=css_names,
        r_values=get_r_values(timestamp),
        cases_rate=latest_rate_by_metric(timestamp, "newCasesBySpecimenDate"),
        deaths_rate=latest_rate_by_metric(timestamp, "newDeaths28DaysByDeathDate"),
        timestamp=website_timestamp,
        **data
    )


def main(req: HttpRequest, context: Context, latestPublished: str,
         websiteTimestamp: str) -> HttpResponse:
    global timestamp, website_timestamp
    timestamp = latestPublished
    website_timestamp = websiteTimestamp
    # cache_client.clear()

    try:
        application = WsgiMiddleware(app.wsgi_app)
        return application.main(req, context)
    except Exception as err:
        logging.exception(err)
