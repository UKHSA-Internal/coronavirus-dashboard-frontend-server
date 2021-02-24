#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from datetime import datetime
from os.path import abspath, split as split_path, join as join_path
from operator import itemgetter
from json import load
from typing import Union, Any

# 3rd party:
from starlette.templating import Jinja2Templates

from pandas import DataFrame

# Internal:
from .types import AlertsType, QueryDataType, AlertLevel, DataItem
from .utils import get_validated_postcode
from ..common.utils import get_release_timestamp
from ..common.data.variables import DestinationMetrics, IsImproving, NationalAdjectives
from ..database.postgres import Connection
from ..config import Settings

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'postcode_page'
]


templates = Jinja2Templates(directory=Settings.template_path)

get_area_type = itemgetter("areaType")


curr_dir, _ = split_path(abspath(__file__))
queries_dir = join_path(curr_dir, "queries")
assets_dir = join_path(curr_dir, "assets")

with open(join_path(queries_dir, "local_data.sql")) as fp:
    local_data_query = fp.read()


with open(join_path(assets_dir, "alert_levels.json")) as fp:
    alerts: AlertsType = load(fp)


with open(join_path(assets_dir, "query_params.json")) as fp:
    query_data: QueryDataType = load(fp)


def alert_level(row: DataItem) -> Union[AlertLevel, dict]:
    try:
        area_code, alert, date = row["areaCode"], row["value"], row["date"]
    except TypeError:
        return alerts["default"]

    if area_code[0] == "E":
        if alert == '-99' and date > "2021-01-03":
            alert = "-99|2021-01-03"

        return alerts["E"][alert]

    elif area_code[0] == "S":
        return alerts["S"][alert]

    return alerts["default"]


async def get_postcode_data(conn: Any, timestamp: str, postcode: str) -> DataFrame:
    ts = datetime.fromisoformat(timestamp.replace("5Z", ""))
    partition_ts = f"{ts:%Y_%-m_%-d}"
    partition_ids = [
        f"{partition_ts}|other",
        f"{partition_ts}|ltla",
        f"{partition_ts}|utla",
        f"{partition_ts}|nhstrust",
    ]
    msoa_partition = f"{partition_ts}_msoa"
    msoa_metric = query_data["local_data"]["msoa_metric"]

    query = local_data_query.format(msoa_partition=msoa_partition)

    substitutes = (
        query_data["local_data"]["metrics"],
        postcode,
        partition_ids,
        msoa_metric,
        f"{msoa_metric}%",
        ["%Percentage%", "%Rate%"]
    )

    # log_query = query
    #
    # for index, sub in enumerate(substitutes, start=1):
    #     if not isinstance(sub, list):
    #         log_query = log_query.replace(f"${index}", f"'{sub}'")
    #     else:
    #         log_query = log_query.replace(f"${index}", f"'{{{str.join(',', sub)}}}'")
    #
    # print(log_query)

    values = await conn.fetch(query, *substitutes)

    df = DataFrame(values, columns=query_data["local_data"]["column_names"])

    df.date = df.date.map(lambda x: f"{x:%-d %B %Y}")

    return df


def get_data(metric: str, data: DataFrame) -> DataItem:
    float_metrics = ["Rate", "Percent"]

    try:
        value = data.loc[
            data.metric == metric,
            query_data["local_data"]["getter_metrics"]
        ].iloc[0]
    except IndexError:
        if metric != "alertLevel":
            return dict()

        df = data.loc[data['rank'] == data['rank'].max(), :]
        df.metric = metric
        df.value = None
        value = df.loc[:, query_data["local_data"]["getter_metrics"]].iloc[0]

    result = {
        "date": value.date,
        "areaName": value.areaName,
        "areaType": value.areaType,
        "areaCode": value.areaCode,
        "adjective": NationalAdjectives.get(value.areaName)
    }

    is_float = any(m in metric for m in float_metrics)

    try:
        float_val = float(value[0])
        result["raw"] = float_val

        if (int_val := int(float_val)) == float_val and not is_float:
            result["value"] = format(int_val, ",d")
            return result

        result["value"] = format(float_val, ".1f")
        return result
    except (ValueError, TypeError):
        pass

    result["raw"] = value[0]
    result["value"] = value[0]

    return result


def is_improving(metric: str, value: Union[float, int]) -> Union[bool, None]:
    if value == 0:
        return None

    improving = IsImproving[metric](value)
    if isinstance(improving, bool):
        return improving

    return None


def get_area_data(df: DataFrame) -> DataFrame:
    small_areas = df.sort_values("rank").iloc[0]

    return small_areas


templates.env.filters['get_data'] = get_data


# @postcode_page.route('/search')
async def postcode_page(request) -> templates.TemplateResponse:
    timestamp = await get_release_timestamp()

    postcode_raw = request.query_params["postcode"]
    postcode = get_validated_postcode(postcode_raw)

    async with Connection() as conn:
        data = await get_postcode_data(conn, timestamp, postcode)

    return templates.TemplateResponse(
        "postcode_results.html",
        context={
            "request": request,
            "timestamp": timestamp,
            "cards": DestinationMetrics,
            "data": data,
            "area_data": get_area_data(data),
            "is_improving": is_improving,
            "process_alert": alert_level
        }
    )
