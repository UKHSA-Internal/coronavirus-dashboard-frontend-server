#!/usr/bin python3

"""
<Description of the programme>

Author:        Pouria Hadjibagheri <pouria.hadjibagheri@phe.gov.uk>
Created:       25 Oct 2020
License:       MIT
Contributors:  Pouria Hadjibagheri
"""

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from datetime import datetime
from os.path import abspath, split as split_path, join as join_path

# 3rd party:
from pandas import DataFrame

# Internal:
from ..common.data.variables import DestinationMetrics, IsImproving
from ..common.utils import get_release_timestamp
from .graphics import get_timeseries
from ..database.postgres import Connection
from ..template_processor import render_template

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'home_page',
    'get_home_page'
]


curr_dir, _ = split_path(abspath(__file__))
queries_dir = join_path(curr_dir, "queries")

with open(join_path(queries_dir, "overview_data.sql")) as fp:
    overview_data_query = fp.read()


metrics = [
    'newAdmissions',
    'newAdmissionsChange',
    'newAdmissionsChangePercentage',
    'newAdmissionsRollingSum',
    'newAdmissionsDirection',

    'cumPeopleVaccinatedFirstDoseByPublishDate',
    'cumPeopleVaccinatedSecondDoseByPublishDate',

    'newDeaths28DaysByPublishDate',
    'newDeaths28DaysByPublishDateChange',
    'newDeaths28DaysByPublishDateChangePercentage',
    'newDeaths28DaysByPublishDateRollingSum',
    'newDeaths28DaysByPublishDateDirection',
    'newDeaths28DaysByDeathDateRollingRate',

    'newCasesByPublishDate',
    'newCasesByPublishDateChange',
    'newCasesByPublishDateChangePercentage',
    'newCasesByPublishDateRollingSum',
    'newCasesByPublishDateDirection',
    'newCasesBySpecimenDateRollingRate',

    'newVirusTests',
    'newVirusTestsChange',
    'newVirusTestsChangePercentage',
    'newVirusTestsRollingSum',
    'newVirusTestsDirection',
]


async def get_landing_data(conn, timestamp):
    ts = datetime.fromisoformat(timestamp.replace("5Z", ""))
    query = overview_data_query.format(partition=f"{ts:%Y_%-m_%-d}_other")

    values = conn.fetch(query, ts, metrics)

    df = DataFrame(
        await values,
        columns=["areaCode", "areaType", "areaName", "date", "metric", "value", "rank"]
    )

    df = df.assign(formatted_date=df.date.map(lambda x: f"{x:%-d %B %Y}"))

    return df


def is_improving(metric, value):
    if value == 0:
        return None

    improving = IsImproving[metric](value)
    if isinstance(improving, bool):
        return improving

    return None


async def get_home_page(request, timestamp: str, invalid_postcode=None) -> render_template:
    async with Connection() as conn:
        data = await get_landing_data(conn, timestamp)

        time_series = {
            key: await value
            async for key, value in get_timeseries(conn, timestamp)
        }

    return await render_template(
        request,
        "main.html",
        context={
            "timestamp": timestamp,
            "data": data,
            "cards": DestinationMetrics,
            "plots": time_series,
            "is_improving": is_improving,
            "invalid_postcode": invalid_postcode
        }
    )


async def home_page(request) -> render_template:
    timestamp = await get_release_timestamp()

    return await get_home_page(request, timestamp)
