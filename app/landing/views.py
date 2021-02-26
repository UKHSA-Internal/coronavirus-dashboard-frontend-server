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
from starlette.templating import Jinja2Templates

from pandas import DataFrame

# Internal:
from ..common.data.variables import DestinationMetrics, IsImproving
from ..common.utils import get_release_timestamp
from .graphics import get_timeseries
from ..database.postgres import Connection
from ..config import Settings

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'home_page'
]


templates = Jinja2Templates(directory=Settings.template_path)

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

    'transmissionRateMin',
    'transmissionRateMax',
    'transmissionRateGrowthRateMin',
    'transmissionRateGrowthRateMax'
]


async def get_landing_data(conn, timestamp):
    ts = datetime.fromisoformat(timestamp.replace("5Z", ""))
    query = overview_data_query.format(partition=f"{ts:%Y_%-m_%-d}_other")

    values = conn.fetch(query, ts, metrics)

    df = DataFrame(
        await values,
        columns=["areaCode", "areaType", "areaName", "date", "metric", "value", "rank"]
    )
    df.date = df.date.map(lambda x: f"{x:%-d %B %Y}")

    return df


def is_improving(metric, value):
    if value == 0:
        return None

    improving = IsImproving[metric](value)
    if isinstance(improving, bool):
        return improving

    return None


def get_data(metric, data):
    float_metrics = ["Rate", "Percent"]

    try:
        value = data.loc[data.metric == metric, ["value", "date", "areaName", "areaType"]].values[0]
    except IndexError:
        return None

    result = {
        "date": value[1],
        "areaName": value[2],
        "areaType": value[3],
    }

    is_float = any(m in metric for m in float_metrics)

    try:
        float_val = float(value[0])
        result["raw"] = float_val

        if (int_val := int(float_val)) == float_val and not is_float:
            result["value"] = format(int_val, ",d")
            return result

        result["value"] = format(float_val, ".1f")
        return result
    except ValueError:
        pass

    result["raw"] = value[0]
    result["value"] = value[0]

    return result


templates.env.filters['get_data'] = get_data


async def home_page(request):
    timestamp = await get_release_timestamp()

    async with Connection() as conn:
        data = await get_landing_data(conn, timestamp)
        time_series = {
            key: await value
            async for key, value in get_timeseries(conn, timestamp)
        }

    return templates.TemplateResponse(
        "main.html",
        context={
            "request": request,
            "timestamp": timestamp,
            "data": data,
            "cards": DestinationMetrics,
            "plots": time_series,
            "is_improving": is_improving,
            "DEBUG": Settings.DEBUG
        }
    )
