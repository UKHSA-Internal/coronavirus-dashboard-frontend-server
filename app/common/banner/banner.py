#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from asyncio import get_running_loop
from pathlib import Path

# 3rd party:
from markdown import markdown

# Internal:
from app.caching import from_cache_or_func
from app.database.postgres import Connection

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'get_banners'
]


BANNER_DATA = dict(
    container="publicdata",
    path="assets/cms/changeLog.json"
)

query_path = Path(__file__).parent.joinpath("query.sql").absolute()

with open(query_path) as fp:
    query = fp.read()


async def _get_banners(request, timestamp: str):
    loop = get_running_loop()

    async with Connection(loop=loop) as conn:
        response = await conn.fetch(query)

    results = [
        {
            "timestamp": banner["date"],
            "display_timestamp": f"{banner['date']:%-d %B %Y}",
            "body": markdown(banner["body"])
        }
        for banner in response
    ]

    return results


async def get_banners(request, timestamp):
    response = from_cache_or_func(
        request=request,
        func=_get_banners,
        prefix="FRONTEND::BN::",
        expire=60 * 15,
        with_request=True,
        timestamp=timestamp
    )

    return await response
