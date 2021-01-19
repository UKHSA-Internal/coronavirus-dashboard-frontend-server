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
from flask import render_template, g, Blueprint, make_response, request

# Internal: 
from .utils import get_landing_data

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'home_page'
]


home_page = Blueprint('home_page', __name__)


@home_page.route('/')
def index_get() -> render_template:
    if request.method == "HEAD":
        return make_response("", 200)

    return render_template("main.html", **get_landing_data(g.timestamp))
