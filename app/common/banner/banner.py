#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from json import loads
from datetime import datetime

# 3rd party:
from markdown import markdown
from flask import request, current_app as app

# Internal:
from ...storage import StorageClient

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

    return item


def filter_fn(timestamp):
    path = request.path

    def func(item):
        is_published = item['appearByUpdate'] <= timestamp < item['disappearByUpdate']

        display_uri = item.get("displayUri", list())

        if len(display_uri) > 0:
            return is_published and path.lower() in display_uri

        return is_published

    return func


def get_banners(timestamp):
    with StorageClient(**BANNER_DATA) as client:
        full_data = loads(client.download().readall().decode())

    if full_data is None:
        full_data = list()

    data = map(prep_data, full_data)
    timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    banners = filter(filter_fn(timestamp), data)

    for banner in banners:
        yield {
            "timestamp": banner["appearByUpdate"].date(),
            "display_timestamp": banner["appearByUpdate"].strftime("%d %B %Y"),
            "body": markdown(banner["body"])
        }
