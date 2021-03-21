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
from os import getenv
from datetime import datetime
from operator import itemgetter
from typing import Dict

# 3rd party:

# Internal:
from .visualisation import plot_thumbnail
from .data.queries import get_last_fortnight, change_by_metric
from .data.variables import DestinationMetrics
from app.storage import AsyncStorageClient
from app.config import Settings

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CLOUD_ROLE_NAME = getenv("WEBSITE_SITE_NAME", "landing-page")

get_value = itemgetter("value")
get_area_type = itemgetter("areaType")


# @cache_client.memoize(60 * 60 * 12)
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


def get_card_data(latest_timestamp: str, category: str, metric_data, graph=True):
    metric_name = DestinationMetrics[category]["metric"]

    change = change_by_metric(latest_timestamp, category, postcode=None)

    response = {
        "data": metric_data,
        "change": change,
        "latest_date": metric_data[0]["date"].strftime('%-d %B %Y')
    }

    if graph:
        response["graph"] = plot_thumbnail(metric_data, change, metric_name)

    return response


# @cache_client.memoize(60 * 60 * 6)
def get_fortnight_data(latest_timestamp: str, area_name: str = "United Kingdom") -> Dict[str, dict]:
    result = dict()

    for category, metadata in DestinationMetrics.items():
        metric_name = metadata['metric']
        metric_data = get_last_fortnight(latest_timestamp, area_name, category)
        result[metric_name] = get_card_data(latest_timestamp, category, metric_data)

    return result


# @cache_client.memoize(60 * 60 * 6)
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


def add_cloud_role_name(envelope):
    envelope.tags['ai.cloud.role'] = CLOUD_ROLE_NAME
    return True


async def get_release_timestamp():
    async with AsyncStorageClient(**Settings.latest_published_timestamp) as client:
        data = await client.download()
        timestamp = await data.readall()

    return timestamp.decode()
