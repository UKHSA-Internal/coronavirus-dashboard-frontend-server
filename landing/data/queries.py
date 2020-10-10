#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from datetime import datetime
from typing import Dict, Union, List

# 3rd party:

# Internal:
from . import query_templates as queries
from ..caching import cache_client

try:
    from __app__.database import CosmosDB, Collection
except ImportError:
    from database import CosmosDB, Collection

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'get_last_fortnight',
    'get_data_by_postcode'
]

ProcessedDateType = Dict[str, Union[str, datetime]]
NumericType = Union[int, float]
DatabaseValueType = Union[str, Union[str, NumericType, ProcessedDateType]]
DatabaseRowType = Union[
    Dict[str, DatabaseValueType],
    List[DatabaseValueType]
]
DatabaseOutputType = List[DatabaseRowType]

destination_metrics = {
    'testing': {
        "metric": 'newPCRTestsByPublishDate',
        "caption": "Testing",
        "heading": "PCR tests processed",
    },
    'healthcare': {
        "metric": 'hospitalCases',
        "caption": "Healthcare",
        "heading": "Patients in hospital",
    },
    'cases': {
        "metric": 'newCasesByPublishDate',
        "caption": "Cases",
        "heading": "People tested positive",
    },
    'deaths': {
        "metric": 'newDeaths28DaysByPublishDate',
        "caption": "Deaths",
        "heading": "Deaths within 28 days of positive test",
    },
}

AreaTypeNames = {
    "nhsRegion": "Healthcare Region",
    "ltla": "Local Authority (Lower tier)",
    "utla": "Local Authority (Upper tier)",
    "region": "Region",
    "nation": "Nation"
}

data_db = CosmosDB(Collection.DATA)
lookup_db = CosmosDB(Collection.LOOKUP)


def process_dates(date: str) -> ProcessedDateType:
    result = {
        'date': datetime.strptime(date, "%Y-%m-%d"),
    }

    result['formatted'] = result['date'].strftime('%-d %b %Y')

    return result


@cache_client.memoize(60 * 5)
def get_last_fortnight(timestamp: str, area_name: str, metric: str) -> DatabaseOutputType:
    """
    Retrieves the last fortnight worth of ``metric`` values
    for ``areaName`` as released on ``timestamp``.
    """
    query = queries.DataSinceApril.substitute({
        "metric": metric,
        "areaName": area_name
    })

    params = [
        {"name": "@releaseTimestamp", "value": timestamp},
        {"name": "@areaName", "value": area_name.lower()}
    ]

    result = [
        {**row, **process_dates(row["date"])}
        for row in data_db.query_iter(query, params=params)
    ]

    return result


@cache_client.memoize(60 * 60 * 12)
def get_latest_value(timestamp: str, area_name: str, metric: str):
    """
    Retrieves the latest ``metric`` value
    for ``areaName`` as released on ``timestamp``.
    """
    query = queries.LatestData.substitute({
        "metric": metric,
        "areaName": area_name
    })

    params = [
        {"name": "@releaseTimestamp", "value": timestamp},
        {"name": "@areaName", "value": area_name.lower()}
    ]

    result = data_db.query(query, params=params)
    
    return result[0]["value"]

@cache_client.memoize(60 * 60 * 12)
def get_postcode_areas(postcode):
    query = queries.PostcodeLookup

    params = [
        {"name": "@postcode", "value": postcode.replace(" ", "").upper()},
    ]

    return lookup_db.query(query, params=params)


@cache_client.memoize(60 * 60 * 12)
def get_data_by_code(area_code, timestamp):
    query = queries.LookupByAreaCode

    params = [
        {"name": "@areaCode", "value": area_code},
    ]

    result = lookup_db.query(query, params=params)
    location_data = result.pop()

    results = dict()

    for category, metric_data in destination_metrics.items():
        destination = location_data['destinations'].get(category)

        query = queries.DataByAreaCode.substitute(metric=metric_data["metric"])

        params = [
            {"name": "@seriesDate", "value": timestamp.split('T')[0]},
            {"name": "@releaseTimestamp", "value": timestamp},
            {"name": "@areaName", "value": destination['areaName'].lower()},
            {"name": "@areaType", "value": destination['areaType']},
        ]

        try:
            data = data_db.query(query, params=params)
            latest = data[0]
            area_type = latest.pop("areaType")

            results[category.capitalize()] = {
                "value": latest["value"],
                # "date": process_dates(latest.pop("date"))["formatted"],
                "areaType_formatted": AreaTypeNames[area_type],
                "areaType": area_type,
                "areaName": latest["areaName"],
                "data": [{**item, **process_dates(item['date'])} for item in data],
                **metric_data,
            }
        except IndexError:
            pass

    return results


def get_data_by_postcode(postcode, timestamp):
    # ToDo: Fail for invalid postcodes
    area = get_postcode_areas(postcode)
    area_code = area.pop()['ltla']

    return get_data_by_code(area_code, timestamp)
