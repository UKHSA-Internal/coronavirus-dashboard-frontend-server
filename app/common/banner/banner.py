#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from json import loads
from datetime import datetime

# 3rd party:
from markdown import markdown

# Internal:
from ...storage import AsyncStorageClient

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'get_banners'
]


BANNER_DATA = dict(
    container="publicdata",
    path="assets/cms/banner.json"
)


def prep_data(item):
    item['appearByUpdate'] = datetime.strptime(item['appearByUpdate'], "%Y-%m-%d")
    item['disappearByUpdate'] = datetime.strptime(item['disappearByUpdate'], "%Y-%m-%d")

    if (datestamp := item.get("date")) is not None:
        item['date'] = datetime.strptime(datestamp, "%Y-%m-%d")
    else:
        item['date'] = item['appearByUpdate']

    return item


def filter_fn(request, timestamp):
    def func(item):
        path = request.scope["path"]
        is_published = item['appearByUpdate'] <= timestamp < item['disappearByUpdate']

        display_uri = item.get("displayUri", list())

        if len(display_uri) > 0:
            return is_published and path.lower() in display_uri

        return is_published

    return func


async def get_banners(request, timestamp: str):
    async with AsyncStorageClient(**BANNER_DATA) as client:
        data_io = await client.download()
        raw_data = await data_io.readall()

    full_data = loads(raw_data.decode())

    if full_data is None:
        full_data = list()

    data = map(prep_data, full_data)
    timestamp = datetime.fromisoformat(timestamp[:26])
    banners = filter(filter_fn(request, timestamp), data)

    results = (
        {
            "timestamp": banner["appearByUpdate"].date(),
            "display_timestamp": f"{banner['date']:%-d %B %Y}",
            "body": markdown(banner["body"])
        }
        for banner in banners
    )

    return results
