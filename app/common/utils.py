#!/usr/bin python3

"""
<Description of the programme>

Author:        Pouria Hadjibagheri <pouria.hadjibagheri@phe.gov.uk>
Created:       25 Oct 2020
License:       MIT
Contributors:  Pouria Hadjibagheri
"""

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from datetime import datetime
from operator import itemgetter
from typing import List, Dict

# 3rd party:

# Internal:
from .caching import cache_client
from .visualisation import get_colour, plot_thumbnail
from .data.queries import get_last_fortnight

try:
    from __app__.database import CosmosDB
except ImportError:
    from database import CosmosDB

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Header
__author__ = "Pouria Hadjibagheri"
__copyright__ = "Copyright (c) 2020, Public Health England"
__license__ = "MIT"
__version__ = "0.0.1"
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

get_value = itemgetter("value")
get_area_type = itemgetter("areaType")

main_metric_names: List[str] = [
    "newCasesByPublishDate",
    "newDeaths28DaysByPublishDate",
    "newAdmissions",
    "newPCRTestsByPublishDate",
]


@cache_client.memoize(60 * 60 * 12)
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
        "latest_date": metric_data[0]["date"].strftime('%-d %B %Y')
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
        order_index = order.index(area_type['abbr'])
        if area_type['abbr'] in order and order_index < min_index:
            result = items[item_ind]
            min_index = order_index

    return result
