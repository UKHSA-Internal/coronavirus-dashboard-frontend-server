#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from datetime import datetime
from os.path import abspath, split as split_path, join as join_path
from operator import itemgetter
from json import load
from typing import Union
from collections import defaultdict
from asyncio import gather, get_running_loop, Lock
import ssl

# 3rd party:
import certifi
from pandas import DataFrame, concat

# Internal:
from .types import QueryDataType
from .utils import get_validated_postcode
from app.common.utils import get_release_timestamp
from app.common.data.variables import DestinationMetrics, IsImproving
from app.database.postgres import Connection
from app.template_processor import render_template
from app.caching import FromCacheOrDB, FromCacheOrDBMainData

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'postcode_page'
]


get_area_type = itemgetter("areaType")

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
ssl_context.verify_mode = ssl.CERT_REQUIRED
ssl_context.check_hostname = True
ssl_context.load_default_certs()
ssl_context.load_verify_locations(certifi.where())


curr_dir, _ = split_path(abspath(__file__))
queries_dir = join_path(curr_dir, "queries")
assets_dir = join_path(curr_dir, "assets")


with open(join_path(assets_dir, "query_params.json")) as fp:
    query_data: QueryDataType = load(fp)


with open(join_path(queries_dir, "single_query.sql")) as fp:
    single_query = fp.read()


with open(join_path(queries_dir, "single_query_msoa.sql")) as fp:
    msoa_query = fp.read()


with open(join_path(queries_dir, "locations.sql")) as fp:
    locations_query = fp.read()


@FromCacheOrDBMainData("area")
async def get_data(request, area_type, area_id, timestamp, loop=None):
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

    partition_name = partition_names[area_type]
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
    async with Connection(loop=loop) as conn:
        result = await conn.fetch(query, *args)

    df = DataFrame(
        result,
        columns=query_data["local_data"]["column_names"],
    ).astype(query_data["local_data"]["column_types"])

    return df


@FromCacheOrDB("area-postcode")
async def get_postcode_areas(request, postcode: str, **kwargs):
    loop = get_running_loop()

    async with Connection(loop=loop) as conn:
        area_codes = await conn.fetch(locations_query, postcode)

    return area_codes


async def get_postcode_data(timestamp: str, postcode: str, request) -> DataFrame:
    msoa_metric = query_data["local_data"]["msoa_metric"]
    ts = datetime.fromisoformat(timestamp.replace("5Z", ""))
    partition_ts = f"{ts:%Y_%-m_%-d}"

    loop = get_running_loop()

    area_codes = await get_postcode_areas(request, postcode)

    if not len(area_codes):
        return DataFrame()

    kws = defaultdict(list)
    for area_data in area_codes:
        kws["area_type"].append(area_data["area_type"])
        kws["area_id"].append(area_data["id"])

    data = await get_data(
        request,
        **kws,
        timestamp=partition_ts
    )

    result = concat(data).reset_index(drop=True)
    result["rank"] = (
         result
         .groupby("metric")[["priority", "date"]]
         .rank(ascending=True)
         .mean(axis=1)
    )
    filters = (
        (result["rank"] < 2) |
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
    timestamp = await get_release_timestamp(request)

    postcode_raw = request.query_params["postcode"]
    postcode = get_validated_postcode(postcode_raw)

    data = await get_postcode_data(timestamp, postcode, request)

    if not data.size:
        return await invalid_postcode_response(
            request,
            timestamp,
            postcode_raw
        )

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

