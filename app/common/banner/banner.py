#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from json import loads
from datetime import datetime

# 3rd party:
from markdown import markdown
from flask import current_app as app

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


def get_banners(timestamp):
    with StorageClient(**BANNER_DATA) as client:
        full_data = loads(client.download().readall().decode())

    data = map(prep_data, full_data)
    timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")

    banners = filter(
        lambda item: item['appearByUpdate'] <= timestamp < item['disappearByUpdate'],
        data
    )

    for banner in banners:
        yield {
            "timestamp": banner["appearByUpdate"].date(),
            "display_timestamp": banner["appearByUpdate"].strftime("%d %B %Y"),
            "body": markdown(banner["body"])
        }
