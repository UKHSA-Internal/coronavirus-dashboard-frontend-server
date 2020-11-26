#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import re
from operator import itemgetter
from typing import List, Dict, Union
from functools import lru_cache

# 3rd party:

# Internal:
from ..common.caching import cache_client
from ..common.data.queries import get_last_fortnight, change_by_metric
from ..common.visualisation import plot_thumbnail, get_colour

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

postcode_pattern = re.compile(r'(^[a-z]{1,2}\d{1,2}[a-z]?\s?\d{1,2}[a-z]{1,2}$)', re.I)
get_value = itemgetter("value")

main_metric_names: List[str] = [
    "newCasesByPublishDate",
    "newDeaths28DaysByPublishDate",
    "newAdmissions",
    "newPCRTestsByPublishDate",
]


@lru_cache(maxsize=256)
def get_validated_postcode(params: dict) -> Union[str, None]:
    found = postcode_pattern.search(params.get("postcode", "").strip())

    if found is not None:
        extract = found.group(0)
        return extract

    return None


# @lru_cache(maxsize=256)


@cache_client.memoize(60 * 60 * 6)
def get_card_data(timestamp: str, metric_name: str, metric_data, graph=True, postcode=None):
    change = change_by_metric(timestamp, metric_name, postcode)
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


@lru_cache(maxsize=256)
def get_fortnight_data(latest_timestamp: str,
                       area_name: str = "United Kingdom") -> Dict[str, dict]:
    result = dict()

    for name in main_metric_names:
        metric_data = get_last_fortnight(latest_timestamp, area_name, name)
        result[name] = get_card_data(name, metric_data)

    return result
