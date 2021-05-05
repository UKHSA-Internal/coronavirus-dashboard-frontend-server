#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import re
from json import loads
from datetime import datetime

# 3rd party:

# Internal:
from app.storage import AsyncStorageClient
from app.caching import from_cache_or_func

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'get_whats_new_banners'
]


BANNER_DATA = dict(
    container="publicdata",
    path="assets/cms/changeLog.json"
)

special_chars_pattern = re.compile(r"[\"')]")
to_underscore_pattern = re.compile(r"[\s.(&,]+")


async def _get_whats_new_banners(timestamp: str):
    async with AsyncStorageClient(**BANNER_DATA) as client:
        data_io = await client.download()
        raw_data = await data_io.readall()

    full_data = loads(raw_data.decode())

    if full_data is None:
        full_data = dict()

    data = full_data.get("changeLog", list())
    datestamp = timestamp.split("T")[0]

    filtered_data = filter(
        lambda b: b["date"] == datestamp and b.get("displayBanner", False),
        data
    )

    results = list()

    for banner in filtered_data:
        banner['anchor'] = special_chars_pattern.sub("", banner["headline"].lower())
        banner['anchor'] = to_underscore_pattern.sub("_", banner["anchor"])
        banner['formatted_date'] = f"{datetime.strptime(banner['date'], '%Y-%m-%d'):%-d %B %Y}"
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
