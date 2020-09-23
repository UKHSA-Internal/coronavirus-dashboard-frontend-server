#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
import re
from operator import itemgetter
from datetime import datetime
from gzip import compress
from os.path import abspath, join as join_path, pardir

# 3rd party:
from flask import Flask, render_template, request, Response
from azure.functions import HttpRequest, HttpResponse, WsgiMiddleware, Context
from typing import Any
from flask_minify import minify

# Internal:
from .visualisation import plot_thumbnail, get_colour
from .data.queries import get_last_fortnight, get_data_by_postcode

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

timestamp = str()

instance_path = abspath(join_path(abspath(__file__), pardir))

app = Flask(__name__, instance_path=instance_path)

app.config.from_object('__app__.landing.config.Config')

minifier = minify(
    html=True,
    js=True,
    cssless=True,
    caching_limit=0,
    fail_safe=True
)

postcode_pattern = re.compile(r'^[a-z]{1,2}\d{1,2}[a-z]?\s?\d{1,2}[a-z]{1,2}$', re.I)

get_value = itemgetter("value")
get_area_type = itemgetter("areaType")

IsImproving = {
    "newCasesByPublishDate": lambda x: x < 0,
    "newDeaths28DaysByPublishDate": lambda x: x < 0,
    "newPillarOneTwoTestsByPublishDate": lambda x: x > 0,
    "hospitalCases": lambda x: x < 0,
}


@app.template_filter()
def format_number(value: Any) -> Any:
    try:
        value_int = int(value)
    except TypeError:
        return value

    if value == value_int:
        return format(value_int, ',d')

    return value


def get_change(metric_data):
    sigma_this_week = sum(map(get_value, metric_data[:7]))
    sigma_last_week = sum(map(get_value, metric_data[7:14]))
    delta = sigma_this_week - sigma_last_week

    delta_percentage = (sigma_this_week / max(sigma_last_week, 0.5) - 1) * 100

    logging.info(delta_percentage)

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
    colour = get_colour(change, IsImproving[metric_name])

    response = {
        "data": metric_data,
        "change": change,
        "is_improving": IsImproving[metric_name],
        "colour": colour,
        "latest_date": metric_data[0]["date"].strftime('%-d %B')
    }

    if graph:
        response["graph"] = plot_thumbnail(metric_data, change, IsImproving[metric_name])

    return response


def get_fortnight_data(area_name: str = "United Kingdom"):
    metric_names = [
        "newCasesByPublishDate",
        "newDeaths28DaysByPublishDate",
        "newPillarOneTwoTestsByPublishDate",
        "hospitalCases",
    ]

    global timestamp

    result = dict()

    for name in metric_names:
        metric_data = get_last_fortnight(timestamp, area_name, name)
        result[name] = get_card_data(name, metric_data)

    return result


def get_main_data():
    # ToDo: Integrate this with postcode data.
    data = get_fortnight_data()

    result = dict(
        cards=[
            {
                "caption": "Testing",
                "heading": "Tests in pillars 1 & 2",
                **data['newPillarOneTwoTestsByPublishDate'],
                "data": data['newPillarOneTwoTestsByPublishDate']['data'],
            },
            {
                "caption": "Healthcare",
                "heading": "Patients in hospital",
                **data['hospitalCases'],
                "data": data['hospitalCases']['data'],
            },
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

            }
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


@app.after_request
def prepare_response(resp: Response):
    global timestamp

    last_modified = datetime.strptime(
        timestamp[:24] + "Z",
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )

    resp.headers['Last-Modified'] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")

    minified = [minifier.get_minified(item.decode(), 'html') for item in resp.response]
    data = str.join("", minified).encode()

    accept_encoding = request.headers.get("Accept-Encoding", "")

    if 'gzip' in accept_encoding:
        data = compress(data)
        resp.headers['Content-Encoding'] = "gzip"

    resp.set_data(data)
    return resp


def get_validated_postcode(params):
    found = postcode_pattern.search(params.get("postcode", "").strip())

    if found is not None:
        extract = found.group(0)
        return extract

    return None


@app.route('/search', methods=['GET'])
def postcode_search() -> render_template:
    postcode = get_validated_postcode(request.args)

    data = get_main_data()

    if postcode is None:
        return render_template(
            "main.html",
            invalid_postcode=True,
            **data
        )

    global timestamp

    try:
        response = {
            category: {
                **values,
                **get_card_data(values["metric"], values['data'], False)
            }
            for category, values in get_data_by_postcode(postcode, timestamp).items()
        }
    except IndexError:
        return render_template(
            "main.html",
            invalid_postcode=True,
            **data
        )

    return render_template(
        "main.html",
        postcode_data=response,
        postcode=postcode.upper(),
        smallest_area=get_by_smallest_areatype(list(response.values()), get_area_type),
        **data
    )


@app.route('/', methods=['GET'])
def index() -> render_template:
    data = get_main_data()
    return render_template("main.html", **data)


def main(req: HttpRequest, context: Context, latestPublished: str) -> HttpResponse:
    logging.info(req.url)

    global timestamp
    timestamp = latestPublished

    application = WsgiMiddleware(app)
    return application.main(req, context)
