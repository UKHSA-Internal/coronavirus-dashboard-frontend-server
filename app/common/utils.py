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
from typing import Dict

# 3rd party:

# Internal:
from .caching import cache_client
from .visualisation import get_colour, plot_thumbnail
from .data.queries import get_last_fortnight, change_by_metric
from .data.constants import DestinationMetrics

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

get_value = itemgetter("value")
get_area_type = itemgetter("areaType")


@cache_client.memoize(60 * 60 * 12)
def get_og_image_names(latest_timestamp: str) -> list:
    ts_python_iso = latest_timestamp[:-2]
    ts = datetime.fromisoformat(ts_python_iso)
    date = ts.strftime("%Y%m%d")
    og_names = [
        f"/downloads/og-images/og-{metric['metric']}_{date}.png"
        for metric in DestinationMetrics.values()
    ]

    og_names.insert(0, f"/downloads/og-images/og-summary_{date}.png")

    return og_names


def get_card_data(latest_timestamp: str, metric_name: str, metric_data, graph=True):
    change = change_by_metric(latest_timestamp, metric_name, postcode=None)
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

    for item in DestinationMetrics.values():
        metric_name = item['metric']
        metric_data = get_last_fortnight(latest_timestamp, area_name, metric_name)
        result[metric_name] = get_card_data(latest_timestamp, metric_name, metric_data, area_name)

    return result


@cache_client.memoize(60 * 60 * 6)
def get_main_data(latest_timestamp: str):
    # ToDo: Integrate this with postcode data.
    data = get_fortnight_data(latest_timestamp)

    cards = [
        {**item, **data[item['metric']], "data": data[item["metric"]]['data']}
        for item in DestinationMetrics.values()
    ]

    return dict(cards=cards)


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
