#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from datetime import datetime, timedelta
from typing import Dict, NamedTuple, List
from functools import lru_cache
from json import dumps

# 3rd party:
from flask import current_app as app
from azure.core.exceptions import AzureError

# Internal:
from . import query_templates as queries
from . import variables as const, dtypes
from ..caching import cache_client
from ..exceptions import InvalidPostcode
from ...database import CosmosDB, Collection

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'get_last_fortnight',
    'get_data_by_postcode',
    'get_msoa_data',
    'get_latest_value',
    'get_r_values',
    'get_alert_level',
    'get_postcode_areas',
    'latest_rate_by_metric',
    'change_by_metric',
    'get_vaccinations'
]


data_db = CosmosDB(Collection.DATA)
lookup_db = CosmosDB(Collection.LOOKUP)
weekly_db = CosmosDB(Collection.WEEKLY)


class AreaType(NamedTuple):
    msoa = "msoa"
    lower_tier_la = "ltla"
    upper_tier_la = "utla"
    region = "region"
    nhs_region = "nhsRegion"
    nhs_trust = "nhsTrust"
    nation = "nation"
    uk = "overview"


def process_dates(date: str) -> dtypes.ProcessedDateType:
    result: dict = {
        'date': datetime.strptime(date, "%Y-%m-%d"),
    }

    result['formatted'] = result['date'].strftime('%-d %B %Y')

    return result


@cache_client.memoize(60 * 5)
def get_last_fortnight(timestamp: str, area_name: str, category: str) -> dtypes.DatabaseOutputType:
    """
    Retrieves the last fortnight worth of ``metric`` values
    for ``areaName`` as released on ``timestamp``.
    """
    metric = const.DestinationMetrics[category]["metric"]

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
        for row in data_db.query_iter(query, params=params)
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

    result = data_db.query(query, params=params)
    
    return result[0]["value"]


# def log_azure_exception(func):
#     @wraps(func)
#     def log_exception(*args, **kwargs):
#         try:
#             query, params, result = func(*args, **kwargs)
#             return result
#         except AzureError as err:
#             logger.exception(err, extra={
#                 "custom_dimensions": {
#                     "query": query,
#                     "query_params": dumps(params)
#                 }
#             })
#             raise err
#     return func


@cache_client.memoize(60 * 60 * 12)
def get_postcode_areas_from_db(postcode):
    query = queries.PostcodeLookup

    params = [
        {"name": "@postcode", "value": postcode.replace(" ", "").upper()},
    ]

    try:
        result = lookup_db.query(query, params=params)

        if not result:
            raise InvalidPostcode(postcode)

        return result.pop()

    except AzureError as err:
        app.logger.exception(err, extra={
            "custom_dimensions": {
                "query": query,
                "query_params": dumps(params)
            }
        })
        raise err


@lru_cache(maxsize=256)
def get_postcode_areas(postcode) -> Dict[str, str]:
    return get_postcode_areas_from_db(postcode)


@cache_client.memoize(60 * 60 * 24)
def get_r_values(latest_timestamp: str, area_name: str = "United Kingdom") -> Dict[str, dict]:
    query = queries.LatestTransmissionRate

    params = [
        {"name": "@releaseTimestamp", "value": latest_timestamp},
        {"name": "@areaName", "value": area_name.lower()}
    ]

    result = data_db.query(query, params=params).pop()

    result['date'] = process_dates(result['date'])['formatted']

    return result


@cache_client.memoize(60 * 60 * 24)
def get_vaccinations(latest_timestamp: str, area_name: str = "United Kingdom") -> Dict[str, dict]:
    query = queries.Vaccinations

    params = [
        {"name": "@releaseTimestamp", "value": latest_timestamp},
        {"name": "@areaName", "value": area_name.lower()}
    ]

    result = data_db.query(query, params=params).pop()

    result['date'] = process_dates(result['date'])['formatted']

    return result


@cache_client.memoize(60 * 60 * 12)
def get_data_by_code(area, timestamp, area_type=AreaType.lower_tier_la):
    # lower_tier_la = 'ltla'
    query = queries.LookupByAreaCode

    params = [
        {"name": "@areaCode", "value": area[area_type]},
    ]

    result = lookup_db.query(query, params=params)
    try:
        location_data = result.pop()
    except IndexError as err:
        app.logger.critical(f"Missing lookup value for {params}")
        raise err

    results = dict()

    for category, metric_data in const.DestinationMetrics.items():
        destination = location_data['destinations'].get(category)

        query = queries.DataByAreaCode.substitute(metric=metric_data["metric"])

        area_type = destination['areaType']

        if category == "healthcare" and area["nation"][0].upper() == "E":
            area_type = "nhsTrust"

        params = [
            {"name": "@seriesDate", "value": timestamp.split('T')[0]},
            {"name": "@releaseTimestamp", "value": timestamp},
            {"name": "@areaCode", "value": area[area_type]},
            {"name": "@areaType", "value": area_type},
        ]

        try:
            data = data_db.query(query, params=params)
            latest = data[0]
            area_type = latest.pop("areaType")

            results[category] = {
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
        data: Dict[str, dict] = weekly_db.query(query, params=params).pop()
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
def get_alert_level(postcode, timestamp, area_type=AreaType.lower_tier_la):
    area = get_postcode_areas(postcode)
    area_code = area[area_type]

    query = queries.AlertLevel
    params = [
        {"name": "@releaseTimestamp", "value": timestamp},
        {"name": "@areaType", "value": area_type},
        {"name": "@areaCode", "value": area_code},
    ]

    try:
        response = data_db.query(query, params=params).pop()
        return response
    except (KeyError, IndexError):
        return None


@cache_client.memoize(60 * 60 * 6)
def latest_rate_by_metric(timestamp, metric, ltla=False, postcode=None):
    lower_tier_la, nation = 'ltla', 'nation'
    nhs_region, nhs_trust = 'nhsRegion', 'nhsTrust'
    england = 'E'

    last_published = datetime.strptime(timestamp.split('T')[0], "%Y-%m-%d")

    offset = 5 if "admissions" not in metric.lower() else 0

    latest_date = (last_published - timedelta(days=offset)).strftime("%Y-%m-%d")

    if ltla:
        area = get_postcode_areas(postcode)
        nation_abbr = area[nation][0].upper()

        if metric == const.DestinationMetrics["testing"]["metric"]:
            area_type = nation

        elif metric != const.DestinationMetrics["healthcare"]["metric"]:
            # Non-healthcare metrics use LTLA.
            area_type = lower_tier_la

        elif metric == const.DestinationMetrics["healthcare"]["metric"] and nation_abbr == england:
            # England uses NHS Region.
            area_type = nhs_trust

        else:
            # DAs don't have NHS Region / trust - switch to nation.
            area_type = nation

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
            {"name": "@areaType", "value": 'overview'},
        ]

    try:
        result = data_db.query(query, params=params)
        latest = max(result, key=lambda x: x['date'])
        response = {
            "date": process_dates(latest['date'])['formatted'],
            "rollingSum": latest['rollingSum'],
            "rollingRate": latest['rollingRate']
        }

        return response

    except (KeyError, IndexError):
        return None


@lru_cache(256)
def get_destinations(area_code):
    query = queries.LookupByAreaCode

    params = [
        {"name": "@areaCode", "value": area_code},
    ]

    destinations = lookup_db.query(query, params=params)
    return destinations


@cache_client.memoize(60 * 60 * 6)
def get_local_card_data(timestamp, category, postcode, change=False) -> dtypes.DatabaseOutputType:
    metric = const.DestinationMetrics[category]['metric']
    latest_date = timestamp.split('T')[0]

    area = get_postcode_areas(postcode)
    area_type = const.DestinationMetrics[category]["postcode_destination"]

    if category == "healthcare" and area["nation"][0].upper() != "E":
        area_type = "nation"
    elif category == "deaths" and area["nation"][0].upper() == "W":
        area_type = "nation"

    area_code = area[area_type]

    if change:
        query = queries.LatestChangeData.substitute(metric=metric)
    else:
        query = queries.SpecimenDateData.substitute(metric=metric)

    params = [
        {"name": "@latestDate", "value": latest_date},
        {"name": "@releaseTimestamp", "value": timestamp},
        {"name": "@areaCode", "value": area_code},
        {"name": "@areaType", "value": area_type},
    ]

    try:
        result = data_db.query(query, params=params)
        return result
    except (KeyError, IndexError):
        return list()


def get_data_by_postcode(postcode, timestamp):
    # ToDo: Fail for invalid postcodes
    area = get_postcode_areas(postcode)

    return get_data_by_code(area, timestamp)


@cache_client.memoize(60 * 60 * 6)
def change_by_metric(timestamp, category, postcode=None):
    if postcode is not None:
        result = get_local_card_data(timestamp, category, postcode, change=True)
    else:
        latest_date = timestamp.split('T')[0]
        metric = const.DestinationMetrics[category]['metric']
        query = queries.LatestChangeDataOverview.substitute(metric=metric)

        params = [
            {"name": "@latestDate", "value": latest_date},
            {"name": "@releaseTimestamp", "value": timestamp},
            {"name": "@areaType", "value": 'overview'},
        ]

        result = data_db.query(query, params=params)

    try:
        response = {
            "value": result[0]["change"],
            "percentage": result[0]["changePercentage"],
            "trend": result[0]["changeDirection"],
            "total": result[0]["rollingSum"]
        }

        return response

    except (KeyError, IndexError):
        return None
