#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from operator import itemgetter
from functools import wraps

# 3rd party:
from flask import render_template, request, g, Blueprint, current_app as app

# Internal: 
from ..common.data.queries import (
    get_data_by_postcode, get_msoa_data, get_r_values, get_alert_level,
    get_postcode_areas, latest_rate_by_metric, get_vaccinations
)

from .utils import get_validated_postcode, get_card_data
from ..common.utils import get_main_data
from ..landing.utils import get_landing_data

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'postcode_page'
]

postcode_page = Blueprint('postcode_page', __name__)

get_area_type = itemgetter("areaType")


def get_by_smallest_areatype(items, areatype_getter):
    order = [
        "lsoa",
        "msoa",
        "ltla",
        "utla",
        "region",
        "nhsTrust",
        "nhsRegion",
        "nation",
        "overview"
    ]
    area_types = map(areatype_getter, items)

    min_index = len(order) - 1
    result = None

    for item_ind, area_type in enumerate(area_types):
        order_index = order.index(area_type['abbr'])
        if area_type['abbr'] in order and order_index < min_index:
            result = items[item_ind]
            min_index = order_index

    return result


def with_globals(view_fn):
    @wraps(view_fn)
    def injector(*args, **kwargs):
        landing_page_kwargs = get_landing_data(g.timestamp)
        response_kws = {
            **landing_page_kwargs,
            **view_fn(*args, **kwargs)
        }
        return render_template(**response_kws)

    return injector


@postcode_page.route('/search')
@with_globals
def postcode_search() -> render_template:
    postcode = get_validated_postcode(request.args)

    data = get_main_data(g.timestamp)

    if postcode is None:
        app.logger.info("Invalid postcode", extra={
            'custom_dimensions': {
                "query_string": request.query_string,
                "validated": False
            }
        })
        return dict(
            **data,
            template_name_or_list="main.html",
            invalid_postcode=True,
            cases_rate=latest_rate_by_metric(g.timestamp, "newCasesBySpecimenDate"),
            deaths_rate=latest_rate_by_metric(g.timestamp, "newDeaths28DaysByDeathDate"),
            admissions_rate=latest_rate_by_metric(g.timestamp, "newAdmissions"),
        )

    app.logger.info("Postcode search", extra={
        'custom_dimensions': {
            "postcode": postcode,
            "validated": True
        }
    })

    try:
        response = {
            category: {
                **values,
                **get_card_data(g.timestamp, category, values['data'], False, postcode)
            }
            for category, values in get_data_by_postcode(postcode, g.timestamp).items()
        }
    except IndexError as err:
        app.logger.exception(err)
        return dict(
            **data,
            template_name_or_list="main.html",
            invalid_postcode=True,
            r_values=get_r_values(g.timestamp),
            vaccinations=get_vaccinations(g.timestamp),
            cases_rate=latest_rate_by_metric(g.timestamp, "newCasesBySpecimenDate"),
            deaths_rate=latest_rate_by_metric(g.timestamp, "newDeaths28DaysByDeathDate"),
            admissions_rate=latest_rate_by_metric(g.timestamp, "newAdmissions"),
        )

    postcode_data = get_postcode_areas(postcode)

    healthcare_region = postcode_data['nhsRegionName']
    nation = postcode_data['nationName']
    if healthcare_region is None:
        healthcare_region = nation

    return dict(
        template_name_or_list="postcode_results.html",
        postcode_data=response,
        postcode=postcode.upper(),
        area_info=postcode_data,
        cases_rate=latest_rate_by_metric(g.timestamp, "newCasesBySpecimenDate", True, postcode),
        admissions_rate=latest_rate_by_metric(g.timestamp, "newAdmissions", True, postcode),
        r_values=get_r_values(g.timestamp, healthcare_region),
        vaccinations=get_vaccinations(g.timestamp, nation),
        smallest_area=get_by_smallest_areatype(list(response.values()), get_area_type),
        alert_level=get_alert_level(postcode, g.timestamp),
        msoa=get_msoa_data(postcode, g.timestamp),
        **data
    )
