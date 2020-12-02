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

# 3rd party:
from flask import render_template, Blueprint, g

# Internal: 
from ..common.caching import cache_client
from ..common.utils import get_main_data, get_notification_content
from ..common.data.queries import get_r_values, latest_rate_by_metric

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Header
__author__ = "Pouria Hadjibagheri"
__copyright__ = "Copyright (c) 2020, Public Health England"
__license__ = "MIT"
__version__ = "0.0.1"
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'home_page'
]


home_page = Blueprint('home_page', __name__)


@home_page.route('/')
@cache_client.cached(timeout=120)
def index() -> render_template:

    data = get_main_data(g.timestamp)
    return render_template(
        "main.html",
        changelog = get_notification_content(g.timestamp),
        r_values=get_r_values(g.timestamp),
        cases_rate=latest_rate_by_metric(g.timestamp, "newCasesBySpecimenDate"),
        deaths_rate=latest_rate_by_metric(g.timestamp, "newDeaths28DaysByDeathDate"),
        admissions_rate=latest_rate_by_metric(g.timestamp, "newAdmissions"),
        **data
    )
