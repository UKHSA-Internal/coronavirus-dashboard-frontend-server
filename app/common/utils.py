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
from .data.variables import DestinationMetrics
from app.storage import AsyncStorageClient
from app.config import Settings
from app.caching import from_cache_or_func

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
    envelope.tags['ai.cloud.role'] = Settings.cloud_role_name
    return True


async def get_from_storage(*args, **kwargs):
    async with AsyncStorageClient(*args, **kwargs) as client:
        data_io = await client.download()
        data_bytes = await data_io.readall()

    return data_bytes.decode()


async def get_release_timestamp(request):
    response = from_cache_or_func(
        request=request,
        func=get_from_storage,
        prefix="FRONTEND::TS::",
        expire=60 * 60,
        **Settings.latest_published_timestamp
    )

    return await response


async def get_website_timestamp(request):
    response = from_cache_or_func(
        request=request,
        func=get_from_storage,
        prefix="FRONTEND::TS::",
        expire=60 * 60,
        **Settings.latest_published_timestamp
    )

    return await response
