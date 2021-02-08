#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import re
from json import loads
from datetime import datetime

# 3rd party:
from markdown import markdown
from flask import request, current_app as app

# Internal:
from ...storage import StorageClient

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


def get_whats_new_banners(timestamp: str):
    with StorageClient(**BANNER_DATA) as client:
        full_data = loads(client.download().readall().decode())

    if full_data is None:
        full_data = dict()

    data = full_data.get("changeLog", list())
    datestamp = timestamp.split("T")[0]

    filtered_data = filter(
        lambda b: b["date"] == datestamp and b.get("displayBanner", False),
        data
    )

    for banner in filtered_data:
        banner['anchor'] = special_chars_pattern.sub("", banner["headline"].lower())
        banner['anchor'] = to_underscore_pattern.sub("_", banner["anchor"])
        banner['formatted_date'] = f"{datetime.strptime(banner['date'], '%Y-%m-%d'):%-d %B %Y}"

        yield banner
