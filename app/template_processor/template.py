#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from functools import wraps
from datetime import datetime, timedelta
from asyncio import gather
from typing import Union, Dict, Any, Optional
import re

# 3rd party:
from starlette.templating import Jinja2Templates
from jinja2.filters import do_mark_safe

from pandas import DataFrame

from pytz import timezone

# Internal: 
from ..config import Settings
from .types import DataItem
from ..common.data.variables import NationalAdjectives
from ..common.utils import get_website_timestamp, get_release_timestamp
from ..common.banner import get_banners
from ..common.whats_new import get_whats_new_banners
from app.common.utils import get_og_image_names

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'template',
    'as_template_filter',
    'render_template'
]


NOT_AVAILABLE = "N/A"

getter_metrics = [
    "value",
    "date",
    "formatted_date",
    "areaName",
    "areaType",
    "areaCode",
    "rank"
]

SUPPRESSED_MSOA = -999999.0
timestamp_pattern = "%A %-d %B %Y at %-I:%M %p"
timezone_LN = timezone("Europe/London")


template = Jinja2Templates(directory=Settings.template_path)


AreaTypeNames = {
    "nhsRegion": "Healthcare Region",
    "nhsTrust": "Healthcare Trust",
    "ltla": "Local Authority (Lower tier)",
    "utla": "Local Authority (Upper tier)",
    "region": "Region",
    "nation": "Nation"
}


def as_template_filter(func):
    template.env.filters[func.__name__] = func

    @wraps(func)
    def add_filter(*args, **kwargs):
        return func(*args, **kwargs)

    return add_filter


async def render_template(request, template_name: str, context: Optional[Dict[str, Any]],
                          status_code: int = 200) -> template.TemplateResponse:
    context = {
        "DEBUG": Settings.DEBUG,
        **context
    }

    if "timestamp" not in context:
        context["timestamp"] = await get_release_timestamp(request)

    if "despatch" not in context:
        context["despatch"] = await get_website_timestamp(request)

    context["date"] = context["despatch"].split("T")[0]

    context["base"] = f"{request.url.scheme}://{request.url.hostname}"

    if request.url.port and request.url.port not in [80, 443]:
        context["base"] += f":{request.url.port}"

    kw_jobs = {
        "banners": get_banners(request, context["timestamp"]),
        "whatsnew_banners": get_whats_new_banners(request, context["timestamp"])
    }

    return template.TemplateResponse(
        template_name,
        status_code=status_code,
        context=dict(
            request=request,
            environment=Settings.ENVIRONMENT,
            app_insight_token=Settings.instrumentation_key,
            og_images=get_og_image_names(context["timestamp"]),
            **dict(zip(kw_jobs, await gather(*kw_jobs.values()))),
            **context
        )
    )


def process_msoa(value: float, metric: str) -> str:
    if value == SUPPRESSED_MSOA:
        if "RollingSum" in metric:
            return do_mark_safe("0 &ndash; 2")
        return NOT_AVAILABLE

    if "RollingSum" in metric:
        return format(int(value), ",d")

    return str(value)


@as_template_filter
def format_number(value: Union[int, float, str]) -> str:
    try:
        value = int(value)
        return format(value, ',d')
    except (ValueError, TypeError):
        pass

    try:
        value = float(value)
        return format(value, ',.1f')
    except (ValueError, TypeError):
        return NOT_AVAILABLE


@as_template_filter
def get_data(metric: str, data: DataFrame, msoa=False) -> DataItem:
    float_metrics = ["Rate", "Percent"]

    try:
        if msoa is not True:
            dt = data.loc[
                ((data.metric == metric) & (data.areaType != "msoa")),
                getter_metrics
            ]
        else:
            dt = data.loc[data.metric == metric, getter_metrics]

        dt = dt.loc[dt["rank"] == dt["rank"].min(), :]
        value = dt.iloc[0]
    except IndexError:
        if metric != "alertLevel":
            return dict()

        df = data.loc[data['rank'] == data['rank'].max(), :]
        df.metric = metric
        df.value = None
        value = df.loc[:, getter_metrics].iloc[0]

    result = {
        "rawDate": value.date,
        "date": value.formatted_date,
        "areaName": value.areaName,
        "areaType": value.areaType,
        "areaCode": value.areaCode,
        "adjective": NationalAdjectives.get(value.areaName)
    }

    is_float = any(m in metric for m in float_metrics)

    try:
        float_val = float(value[0])
        result["raw"] = float_val

        if value.areaType == 'msoa':
            result["value"] = process_msoa(float_val, metric)
            return result

        if (int_val := int(float_val)) == float_val and not is_float:
            result["value"] = format(int_val, ",d")
            return result

        result["value"] = format(float_val, ".1f")
        return result
    except (ValueError, TypeError):
        pass

    result["value"] = value[0]
    result["raw"] = value[0]

    return result


@as_template_filter
def trim_area_name(area_name):
    pattern = re.compile(r"(nhs\b.*)", re.IGNORECASE)
    name = pattern.sub("", area_name)

    return name.strip()


@as_template_filter
def to_full_area_type(area_type: str) -> str:
    return AreaTypeNames.get(area_type, area_type)


@as_template_filter
def format_timestamp(latest_timestamp: str) -> str:
    ts_python_iso = latest_timestamp[:26] + "+00:00"
    ts = datetime.fromisoformat(ts_python_iso)
    ts_london = ts.astimezone(timezone_LN)
    formatted = ts_london.strftime(timestamp_pattern)
    result = re.sub(r'\s([AP]M)', lambda found: found.group(1).lower(), formatted)
    return result


@as_template_filter
def format_date(date: datetime) -> str:
    return do_mark_safe(f"{date:%-d %B %Y}")


@as_template_filter
def subtract_days(date: datetime, days: int) -> datetime:
    return date - timedelta(days=days)


@as_template_filter
def add_days(date: Union[datetime, str], days: int) -> datetime:
    if isinstance(date, datetime):
        return date + timedelta(days=days)

    return datetime.fromisoformat(date.removesuffix("5Z")) + timedelta(days=1)


@as_template_filter
def pluralise(number, singular, plural, null=str()):
    if abs(number) > 1:
        return plural

    if abs(number) == 1:
        return singular

    if number == 0 and not len(null):
        return plural

    return null


@as_template_filter
def comparison_verb(number, greater, smaller, same):
    if number > 0:
        return greater

    if number < 0:
        return smaller

    return same
