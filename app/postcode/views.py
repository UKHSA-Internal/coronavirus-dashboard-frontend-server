#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from datetime import datetime, timedelta
from os.path import abspath, split as split_path, join as join_path
from operator import itemgetter
from json import load
from typing import Union
from asyncio import gather
from hashlib import blake2b
from io import BytesIO
from random import randint
from functools import wraps

# 3rd party:

from pandas import DataFrame, concat, read_pickle

# Internal:
from .types import QueryDataType
from .utils import get_validated_postcode
from app.common.utils import get_release_timestamp
from app.common.data.variables import DestinationMetrics, IsImproving
from app.database.postgres import Connection
from app.template_processor import render_template
from app.caching import Redis

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'postcode_page'
]


get_area_type = itemgetter("areaType")


curr_dir, _ = split_path(abspath(__file__))
queries_dir = join_path(curr_dir, "queries")
assets_dir = join_path(curr_dir, "assets")

with open(join_path(queries_dir, "local_data_se.sql")) as fp:
    local_data_query = fp.read()


with open(join_path(assets_dir, "query_params.json")) as fp:
    query_data: QueryDataType = load(fp)


with open(join_path(queries_dir, "single_query.sql")) as fp:
    single_query = fp.read()


with open(join_path(queries_dir, "single_query_msoa.sql")) as fp:
    msoa_query = fp.read()


with open(join_path(queries_dir, "locations.sql")) as fp:
    locations_query = fp.read()


def from_cache_or_db(prefix):
    def outer(func):
        @wraps(func)
        async def inner(*args, **kwargs):

            raw_key = prefix + str.join("|", map(str, [*args, *kwargs.values()]))
            cache_key = blake2b(raw_key.encode(), digest_size=6).hexdigest()

            redis = Redis(raw_key)

            buffer = BytesIO()
            if (redis_result := await redis.get(cache_key)) is not None:
                buffer.write(redis_result)
                buffer.seek(0)
                result = read_pickle(buffer)
                return result

            result: DataFrame = await func(*args, **kwargs)
            result.to_pickle(buffer)
            buffer.seek(0)
            await redis.set(cache_key, buffer.read(), randint(30, 300) * 60)
            return result

        return inner
    return outer


@from_cache_or_db("FRONTEND::PC::")
async def get_data(partition_name, area_type, area_id, timestamp):
    numeric_metrics = ["%Percentage%", "%Rate%"]
    local_metrics = query_data["local_data"]["metrics"]
    msoa_metric = [f'{query_data["local_data"]["msoa_metric"]}%']

    if area_type == "msoa":
        query = msoa_query
        args = [
            area_id,
            local_metrics,
            msoa_metric
        ]
    else:
        query = single_query
        args = [
            numeric_metrics,
            area_id,
            local_metrics
        ]

    query = query.format(partition_id=f"{timestamp}_{partition_name}")

    async with Connection() as conn:
        result = await conn.fetch(query, *args)

    df = DataFrame(
        result,
        columns=query_data["local_data"]["column_names"],
    ).astype(query_data["local_data"]["column_types"])

    return df


async def get_postcode_data(timestamp: str, postcode: str) -> DataFrame:
    msoa_metric = query_data["local_data"]["msoa_metric"]
    ts = datetime.fromisoformat(timestamp.replace("5Z", ""))
    partition_ts = f"{ts:%Y_%-m_%-d}"
    partition_names = {
        "overview": "other",
        "nation": "other",
        "region": "other",
        "nhsRegion": "other",
        "utla": "utla",
        "ltla": "ltla",
        "nhsTrust": "nhstrust",
        "msoa": "msoa",
    }

    async with Connection() as conn:
        area_codes = await conn.fetch(locations_query, postcode)

    if not len(area_codes):
        return DataFrame()

    tasks = list()
    for area_data in area_codes:
        area_type = area_data["area_type"]
        task = get_data(
            partition_names[area_type],
            area_type,
            area_data["id"],
            partition_ts
        )

        tasks.append(task)

    data = await gather(*tasks)

    result = concat(data).reset_index(drop=True)
    result["rank"] = result.groupby("metric")[["priority", "date"]].rank(ascending=True)
    filters = (
            (result["rank"] == 1) |
            (result["metric"].str.startswith(msoa_metric))
    )
    result = result.loc[filters, :]

    result = result.assign(
        formatted_date=result.date.map(lambda x: f"{x:%-d %B %Y}"),
        postcode=area_codes[0]['postcode']
    )

    return result


def is_improving(metric: str, value: Union[float, int]) -> Union[bool, None]:
    if value == 0:
        return None

    improving = IsImproving[metric](value)
    if isinstance(improving, bool):
        return improving

    return None


def get_area_data(df: DataFrame) -> DataFrame:
    small_areas = df.sort_values("priority").iloc[0]
    return small_areas


async def invalid_postcode_response(request, timestamp, raw_postcode):
    from ..landing.views import get_home_page

    return await get_home_page(
        request=request,
        timestamp=timestamp,
        invalid_postcode=raw_postcode.upper()
    )


async def postcode_page(request) -> render_template:
    timestamp = await get_release_timestamp()

    postcode_raw = request.query_params["postcode"]
    postcode = get_validated_postcode(postcode_raw)

    data = await get_postcode_data(timestamp, postcode)

    if not data.size:
        return await invalid_postcode_response(request, timestamp, postcode_raw)

    return await render_template(
        request,
        "postcode_results.html",
        context={
            "timestamp": timestamp,
            "cards": DestinationMetrics,
            "data": data,
            "area_data": get_area_data(data),
            "is_improving": is_improving
        }
    )

