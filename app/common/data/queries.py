#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from datetime import datetime, timedelta
from typing import Dict
from json import dumps

# 3rd party:
from flask import g, current_app as app
from azure.core.exceptions import AzureError

# Internal:
from . import query_templates as queries
from . import variables as const, dtypes
from ..caching import cache_client
from ..exceptions import InvalidPostcode

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
    'change_by_metric'
]


def process_dates(date: str) -> dtypes.ProcessedDateType:
    result: dict = {
        'date': datetime.strptime(date, "%Y-%m-%d"),
    }

    result['formatted'] = result['date'].strftime('%-d %B %Y')

    return result


@cache_client.memoize(60 * 5)
def get_last_fortnight(timestamp: str, area_name: str, metric: str) -> dtypes.DatabaseOutputType:
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
        result = g.lookup_db.query(query, params=params)

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


def get_postcode_areas(postcode) -> Dict[str, str]:
    return get_postcode_areas_from_db(postcode)


@cache_client.memoize(60 * 60 * 6)
def get_r_values(latest_timestamp: str, area_name: str = "United Kingdom") -> Dict[str, dict]:
    query = queries.LatestTransmissionRate

    params = [
        {"name": "@releaseTimestamp", "value": latest_timestamp},
        {"name": "@areaName", "value": area_name.lower()}
    ]

    result = g.data_db.query(query, params=params).pop()

    result['date'] = process_dates(result['date'])['formatted']

    return result


@cache_client.memoize(60 * 60 * 12)
def get_data_by_code(area, timestamp):
    lower_tier_la = 'ltla'
    query = queries.LookupByAreaCode

    params = [
        {"name": "@areaCode", "value": area[lower_tier_la]},
    ]

    result = g.lookup_db.query(query, params=params)
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
    lower_tier_la = 'ltla'
    area = get_postcode_areas(postcode)
    area_code = area[lower_tier_la]

    query = queries.AlertLevel
    params = [
        {"name": "@releaseTimestamp", "value": timestamp},
        {"name": "@areaType", "value": lower_tier_la},
        {"name": "@areaCode", "value": area_code},
    ]

    try:
        response = g.data_db.query(query, params=params).pop()
        return response
    except (KeyError, IndexError):
        return None


@cache_client.memoize(60 * 60 * 6)
def latest_rate_by_metric(timestamp, metric, ltla=False, postcode=None):
    lower_tier_la, nhs, nation = 'ltla', 'nhsRegion', 'nation'
    england = 'E'

    last_published = datetime.strptime(timestamp.split('T')[0], "%Y-%m-%d")

    offset = 5 if "admissions" not in metric.lower() else 0

    latest_date = (last_published - timedelta(days=offset)).strftime("%Y-%m-%d")

    if ltla:
        area = get_postcode_areas(postcode)
        nation_abbr = area[nation][0].upper()

        if metric != const.DestinationMetrics["healthcare"]["metric"]:
            # Non-healthcare metrics use LTLA.
            area_type = lower_tier_la

        elif nation_abbr == england:
            # England uses NHS Region.
            area_type = nhs

        else:
            # DAs don't have NHS Region - switch to nation.
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
        result = g.data_db.query(query, params=params)
        latest = max(result, key=lambda x: x['date'])
        response = {
            "date": process_dates(latest['date'])['formatted'],
            "rollingSum": latest['rollingSum'],
            "rollingRate": latest['rollingRate']
        }

        return response

    except (KeyError, IndexError):
        return None


def get_data_by_postcode(postcode, timestamp):
    # ToDo: Fail for invalid postcodes
    area = get_postcode_areas(postcode)

    return get_data_by_code(area, timestamp)


@cache_client.memoize(60 * 60 * 6)
def change_by_metric(timestamp, metric, postcode=None):
    last_published = datetime.strptime(timestamp.split('T')[0], "%Y-%m-%d")
    latest_date = last_published.strftime("%Y-%m-%d")

    england = "E"
    england_and_scotland = "ES"
    lower_tier_la, nhs, nation = 'ltla', 'nhsRegion', 'nation'

    if postcode is not None:
        area = get_postcode_areas(postcode)

        nation_abbr = area['nation'][0].upper()

        if metric == const.DestinationMetrics["deaths"]["metric"] and nation_abbr in england_and_scotland:
            # England and Scotland use LTLA for deaths.
            area_type = lower_tier_la

        elif metric == const.DestinationMetrics["healthcare"]["metric"] and nation_abbr in england:
            # England uses NHS Region.
            area_type = nhs

        elif metric == const.DestinationMetrics["cases"]["metric"]:
            # cases are all LTLA
            area_type = lower_tier_la

        else:
            # everything else is national.
            area_type = nation

        area_code = area[area_type]
        query = queries.LatestChangeData.substitute(metric=metric)

        params = [
            {"name": "@latestDate", "value": latest_date},
            {"name": "@releaseTimestamp", "value": timestamp},
            {"name": "@areaCode", "value": area_code},
            {"name": "@areaType", "value": area_type},
        ]
    else:
        query = queries.LatestChangeDataOverview.substitute(metric=metric)

        params = [
            {"name": "@latestDate", "value": latest_date},
            {"name": "@releaseTimestamp", "value": timestamp},
            {"name": "@areaType", "value": 'overview'},
        ]

    try:
        result = g.data_db.query(query, params=params)
        response = {
            "value": result[0]["change"],
            "percentage": result[0]["changePercentage"],
            "trend": result[0]["changeDirection"],
            "total": result[0]["rollingSum"]
        }
        return response

    except (KeyError, IndexError):
        return None
