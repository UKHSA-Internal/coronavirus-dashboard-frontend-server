#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:

# 3rd party:
from flask import render_template, Blueprint, g

# Internal:
from ..common.caching import cache_client
from ..common.utils import get_main_data
from ..common.data.queries import get_r_values, latest_rate_by_metric, get_vaccinations

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'get_landing_data'
]


@cache_client.memoize(timeout=12 * 60 * 60)
def get_landing_data(timestamp):
    response = dict(
        r_values=get_r_values(timestamp),
        vaccinations=get_vaccinations(timestamp),
        cases_rate=latest_rate_by_metric(timestamp, "newCasesBySpecimenDate"),
        deaths_rate=latest_rate_by_metric(timestamp, "newDeaths28DaysByDeathDate"),
        admissions_rate=latest_rate_by_metric(timestamp, "newAdmissions"),
        **get_main_data(timestamp),
    )

    return response
