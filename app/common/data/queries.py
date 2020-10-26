#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from datetime import datetime, timedelta
from typing import Dict
from functools import lru_cache

# 3rd party:
from flask import g

# Internal:
from . import query_templates as queries
from . import constants as const, types
from ..caching import cache_client

try:
    from __app__.database import CosmosDB, Collection
except ImportError:
    from database import CosmosDB, Collection

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'get_last_fortnight',
    'get_data_by_postcode',
    'get_msoa_data',
    'get_latest_value',
    'get_r_values',
    'get_alert_level',
    'get_postcode_areas',
    'latest_rate_by_metric'
]


@lru_cache(maxsize=512)
def process_dates(date: str) -> types.ProcessedDateType:
    result: dict = {
        'date': datetime.strptime(date, "%Y-%m-%d"),
    }

    result['formatted'] = result['date'].strftime('%-d %B %Y')

    return result


@cache_client.memoize(60 * 5)
def get_last_fortnight(timestamp: str, area_name: str, metric: str) -> types.DatabaseOutputType:
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
        {"name": "@areaName", "value": area_name.lower()},
    ]

    result = [
        {**row, **process_dates(row["date"])}
        for row in g.data_db.query_iter(query, params=params)
    ]

    return result


@cache_client.memoize(60 * 60 * 12)
def get_latest_value(metric: str, timestamp: str, area_name: str):
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

    result = g.data_db.query(query, params=params)
    
    return result[0]["value"]


@cache_client.memoize(60 * 60 * 12)
def get_postcode_areas_from_db(postcode):
    query = queries.PostcodeLookup

    params = [
        {"name": "@postcode", "value": postcode.replace(" ", "").upper()},
    ]

    return g.lookup_db.query(query, params=params).pop()


@lru_cache(maxsize=256)
def get_postcode_areas(postcode) -> Dict[str, str]:
    return get_postcode_areas_from_db(postcode)


@cache_client.memoize(60 * 60 * 6)
def get_r_values(latest_timestamp: str, area_name: str = "United Kingdom") -> Dict[str, dict]:
    query = queries.LatestTransmissionRate

    params = [
        {"name": "@releaseTimestamp", "value": latest_timestamp},
        {"name": "@areaName", "value": area_name.lower()}
    ]

    return g.data_db.query(query, params=params).pop()


@cache_client.memoize(60 * 60 * 12)
def get_data_by_code(area, timestamp):
    query = queries.LookupByAreaCode

    params = [
        {"name": "@areaCode", "value": area['ltla']},
    ]

    result = g.lookup_db.query(query, params=params)
    try:
        location_data = result.pop()
    except IndexError as err:
        logging.critical(f"Missing lookup value for {params}")
        raise err

    results = dict()

    for category, metric_data in const.DestinationMetrics.items():
        destination = location_data['destinations'].get(category)

        query = queries.DataByAreaCode.substitute(metric=metric_data["metric"])

        area_type = destination['areaType']
        params = [
            {"name": "@seriesDate", "value": timestamp.split('T')[0]},
            {"name": "@releaseTimestamp", "value": timestamp},
            {"name": "@areaCode", "value": area[area_type]},
            {"name": "@areaType", "value": area_type},
        ]

        try:
            data = g.data_db.query(query, params=params)
            latest = data[0]
            area_type = latest.pop("areaType")

            results[category.capitalize()] = {
                "value": latest["value"],
                "areaType": {
                    "abbr": area_type,
                    "formatted": const.AreaTypeNames[area_type],
                    "short": const.AreaTypeShortNames[area_type]
                },
                "areaName": latest["areaName"],
                "data": [{**item, **process_dates(item['date'])} for item in data],
                **metric_data,
            }
        except IndexError:
            pass

    return results


@cache_client.memoize(60 * 60 * 6)
def get_msoa_data(postcode, timestamp):
    query = queries.MsoaData
    area = get_postcode_areas(postcode)
    area_code = area['msoa']
    area_name = area['msoaName']

    params = [
        {"name": "@id", "value": f"MSOA|{area_code}"}
    ]

    try:
        data: Dict[str, dict] = g.weekly_db.query(query, params=params).pop()
        cases_data: dict = data["latest"]["newCasesBySpecimenDate"]

        response = {
            "areaName": area_name,
            "latestSum": cases_data["rollingSum"],
            "latestRate": cases_data["rollingRate"],
            "latestDate": process_dates(cases_data["date"])["formatted"],
            "dataTimestamp": timestamp
        }

        return response
    except (KeyError, IndexError):
        return None


@cache_client.memoize(60 * 60 * 6)
def get_alert_level(postcode, timestamp):
    area = get_postcode_areas(postcode)
    area_code = area['ltla']

    query = queries.AlertLevel
    params = [
        {"name": "@releaseTimestamp", "value": timestamp},
        {"name": "@areaType", "value": "ltla"},
        {"name": "@areaCode", "value": area_code},
    ]

    try:
        response = g.data_db.query(query, params=params).pop()
        return response
    except (KeyError, IndexError):
        return None


@cache_client.memoize(60 * 60 * 6)
def latest_rate_by_metric(timestamp, metric, ltla=False, postcode=""):
    last_published = datetime.strptime(timestamp.split('T')[0], "%Y-%m-%d")

    offset = 5 if "admissions" not in metric.lower() else 0

    latest_date = (last_published - timedelta(days=offset)).strftime("%Y-%m-%d")

    if ltla:
        area = get_postcode_areas(postcode)

        if metric != const.DestinationMetrics["healthcare"]["metric"]:
            # Non-healthcare metrics use LTLA.
            area_type = 'ltla'
        elif area['nation'][0].upper() not in "SNW":
            # England uses NHS Region.
            area_type = 'nhsRegion'
        else:
            # DAs don't have NHS Region - switch to nation.
            area_type = 'nation'

        area_code = area[area_type]
        query = queries.SpecimenDateData.substitute(metric=metric)

        params = [
            {"name": "@latestDate", "value": latest_date},
            {"name": "@releaseTimestamp", "value": timestamp},
            {"name": "@areaCode", "value": area_code},
            {"name": "@areaType", "value": area_type},
        ]
    else:
        query = queries.SpecimenDateDataOverview.substitute(metric=metric)

        params = [
            {"name": "@latestDate", "value": latest_date},
            {"name": "@releaseTimestamp", "value": timestamp},
            {"name": "@areaType", "value": 'nation'},
        ]

    try:
        result = g.data_db.query(query, params=params)
        latest = max(result, key=lambda x: x['date'])
        response = {
            "date": process_dates(latest['date'])['formatted'],
            "rollingSum": sum(map(lambda x: x['value'], result)),
            "rollingRate": latest['rate']
        }

        return response

    except (KeyError, IndexError):
        return None


def get_data_by_postcode(postcode, timestamp):
    # ToDo: Fail for invalid postcodes
    area = get_postcode_areas(postcode)

    return get_data_by_code(area, timestamp)
