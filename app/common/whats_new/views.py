#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import re
from datetime import datetime
from asyncio import get_running_loop
from pathlib import Path

# 3rd party:

# Internal:
from app.caching import from_cache_or_func
from app.database.postgres import Connection


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'get_whats_new_banners'
]

BANNER_DATA = dict(
    container="publicdata",
    path="assets/cms/changeLog.json"
)

query_path = Path(__file__).parent.joinpath("query.sql").absolute()

with open(query_path) as fp:
    query = fp.read()

special_chars_pattern = re.compile(r"[\"')]")
to_underscore_pattern = re.compile(r"[\s.(&,]+")


async def _get_whats_new_banners(timestamp: str):
    loop = get_running_loop()

    async with Connection(loop=loop) as conn:
        response = await conn.fetch(query, datetime.fromisoformat(timestamp[:-2]))

    results = list()
    for banner in map(dict, response):
        banner["formatted_date"] = f"{banner['date']:%-d %B %Y}"
        banner["date"] = banner['date'].isoformat()
        results.append(banner)

    return results


async def get_whats_new_banners(request, timestamp):
    response = from_cache_or_func(
        request=request,
        func=_get_whats_new_banners,
        prefix="FRONTEND::CL::",
        expire=60 * 15,
        timestamp=timestamp
    )

    return await response
