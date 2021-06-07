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
from random import randint
from asyncio import get_running_loop, Lock

# 3rd party:
from pandas import DataFrame

# Internal:
from app.common.data.variables import DestinationMetrics, IsImproving
from app.common.utils import get_release_timestamp
from app.database.postgres import Connection
from app.template_processor import render_template
from app.caching import from_cache_or_func

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

    "newPeopleVaccinatedFirstDoseByPublishDate",
    "newPeopleVaccinatedSecondDoseByPublishDate",
    "cumPeopleVaccinatedFirstDoseByPublishDate",
    "cumPeopleVaccinatedSecondDoseByPublishDate",
    "cumVaccinationFirstDoseUptakeByPublishDatePercentage",
    "cumVaccinationSecondDoseUptakeByPublishDatePercentage",

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


async def get_landing_data(timestamp):
    ts = datetime.fromisoformat(timestamp.replace("5Z", ""))
    query = overview_data_query.format(partition=f"{ts:%Y_%-m_%-d}_other")

    loop = get_running_loop()

    async with Connection() as conn, Lock(loop=loop):
        values = await conn.fetch(query, ts, metrics)

    df = DataFrame(
        values,
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
    response = await from_cache_or_func(
        request=request,
        func=get_landing_data,
        prefix="FRONTEND::LP::",
        expire=randint(5 * 60, 8 * 60) * 60,  # Between 5 and 8 hours
        timestamp=timestamp
    )

    context = {
        "timestamp": timestamp,
        "data": response,
        "cards": DestinationMetrics,
        "is_improving": is_improving,
        "invalid_postcode": invalid_postcode
    }

    return await render_template(request, "main.html", context=context)


async def home_page(request) -> render_template:
    timestamp = await get_release_timestamp(request)

    return await get_home_page(request, timestamp=timestamp)
