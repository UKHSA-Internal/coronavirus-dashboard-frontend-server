#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from statistics import mean
from operator import itemgetter
from json import dumps

# 3rd party:
from flask import Flask, Response, render_template, request
from azure.functions import HttpRequest, HttpResponse, WsgiMiddleware, Context
from uk_covid19 import Cov19API
from datetime import datetime, timedelta
from typing import Union, Tuple, Any

# Internal:
from .data.queries import get_last_fortnight

try:
   from __app__.database import CosmosDB
   from __app__.storage import StorageClient
except ImportError:
   from database import CosmosDB
   from storage import StorageClient

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'main'
]

timestamp = str()

app = Flask(__name__)

app.config["APPLICATION_ROOT"] = "/"

#storage_client = StorageClient(container='$web', path='index.html')
#template_pointer = storage_client.download()
#template = template_pointer.readall().decode()

# return JSON data for specified parameter from specified JSON data
def get_data(request_json: dict, request_param: str) -> Union[str, None]:
   
    index = 0
    result = request_json["data"][0][request_param]
    while result is None:
        if index == len(request_json["data"]):
            break
        result = request_json["data"][index][request_param]
        index += 1
    return result


# return date for specified parameter from specified JSON data
def get_date(request_json: dict, request_param: str) -> str:

    index = 0
    result = request_json["data"][0][request_param]
    obj_result_date = datetime.strptime(request_json["data"][index]["date"], '%Y-%m-%d')
    result_date = obj_result_date.strftime('%d %B %Y')
    while result is None:
        if index == len(request_json["data"]):
            break
        obj_result_date = datetime.strptime(request_json["data"][index]["date"], '%Y-%m-%d')
        result_date = obj_result_date.strftime('%d %B %Y')
        result = request_json["data"][index][request_param]
        index += 1
    return result_date


# return the prev 7 days of results and the change between the last week and 2 weeks ago as a percentage  of the specified request param
# (trial_change returns the difference as whole number)
def get_week(request_json: dict, request_param: str) -> Tuple[int, Union[int, str], Union[float, str]]:
    # get the dates for a week ago and 2 weeks ago ---- uses 2 weeks data from date of latest entry ----
    week_prev = datetime.strptime(request_json["data"][0]["date"], '%Y-%m-%d') - timedelta(days=6)
    string_week_prev = week_prev.strftime('%Y-%m-%d')
    fortnight_prev = datetime.strptime(request_json["data"][0]["date"], '%Y-%m-%d') - timedelta(days=13)
    string_fortnight_prev = fortnight_prev.strftime('%Y-%m-%d')
    
    week_result_total = 0
    week_complete = False
    fortnight_complete = False
    week_data_present = False
    fortnight_data_present = False
    index = 0
    while not week_complete:
        if request_json["data"][index]["date"] == string_week_prev:
            week_complete = True
            

        if request_json["data"][index][request_param] is None:
            week_result_total += 0
        
        else:
            week_result_total += request_json["data"][index][request_param]
            week_data_present = True

        
        index += 1

    
    fortnight_result_total = 0

    while not fortnight_complete:
        if request_json["data"][index]["date"] == string_fortnight_prev:
            fortnight_complete = True
            

        if request_json["data"][index][request_param] is None:
            fortnight_result_total += 0
        
        else:
            fortnight_result_total += request_json["data"][index][request_param]
            fortnight_data_present = True

        
        index += 1

    if week_data_present and fortnight_data_present:
        
        try:
            division = week_result_total / fortnight_result_total
        except ZeroDivisionError:
            division = 0

        two_week_result_change = round((division) * 100 - 100, 2)
        trial_change = week_result_total - fortnight_result_total
        

    else:
        two_week_result_change = "insuficcent data"
        trial_change = "insufficient data"

    
    return week_result_total, trial_change, two_week_result_change

# Filter for use in templates, adds commas to data e.g. 123456 becomes 123,456


@app.template_filter()
def numberFormat(value: Any) -> Any:
    if value is not None and isinstance(value, int):
        return format(int(value), ',d')
    else:
        return value


# Gets country from dropdown form and returns data for the specified country
@app.route('/areasearch', methods=['POST'])
def regional_data() -> render_template:

    postcode = request.form['postcode']
    drop_down_code = request.form['dropdown']
    # if a postcode has been entered (currently using ONS area codes)
    # then filter by the code provided
    if postcode != '':
        filters_areaCode = [
            f'areaCode={postcode}'
        ]
    # use dropdown item if no postcode provided
    else:
        filters_areaCode = [
            f'areaCode={drop_down_code}'
        ]

    # set API params
    area_api = Cov19API(
        filters=filters_areaCode,
        structure=structure
    )
    # return JSON
    area_data = area_api.get_json()
    # seperate fields into variables for parsing to template

    area_name = get_data(area_data, "areaName")

    area_new_tests = get_data(area_data, "newTestsByPublishDate")

    area_tests_date = get_date(area_data, "newTestsByPublishDate")

    area_new_cases = get_data(area_data, "newCasesByPublishDate")
    area_cases_date = get_date(area_data, "newCasesByPublishDate")

    area_new_admissions = get_data(area_data, "newAdmissions")
    area_admissions_date = get_date(area_data, "newAdmissions")
    
    area_new_deaths = get_data(area_data, "newDeaths28DaysByPublishDate")
    area_deaths_date = get_date(area_data, "newDeaths28DaysByPublishDate")

   
    obj_area_cases_week_prev = datetime.strptime(area_cases_date, '%d %B %Y') - timedelta(days=6)
    area_cases_week_prev = obj_area_cases_week_prev.strftime('%d %B %Y')
    obj_area_cases_fortnight_prev = datetime.strptime(area_cases_date, '%d %B %Y') - timedelta(days=13)
    area_cases_fortnight_prev = obj_area_cases_fortnight_prev.strftime('%d %B %Y')
    obj_area_cases_prev_week_begin = datetime.strptime(area_cases_date, '%d %B %Y') - timedelta(days=7)
    area_prev_cases_week_begin = obj_area_cases_prev_week_begin.strftime('%d %B %Y')

    obj_area_tests_week_prev = datetime.strptime(area_tests_date, '%d %B %Y') - timedelta(days=6)
    area_tests_week_prev = obj_area_tests_week_prev.strftime('%d %B %Y')
    obj_area_tests_fortnight_prev = datetime.strptime(area_tests_date, '%d %B %Y') - timedelta(days=13)
    area_tests_fortnight_prev = obj_area_tests_fortnight_prev.strftime('%d %B %Y')
    obj_area_tests_prev_week_begin = datetime.strptime(area_tests_date, '%d %B %Y') - timedelta(days=7)
    area_prev_tests_week_begin = obj_area_tests_prev_week_begin.strftime('%d %B %Y')

    obj_area_admissions_week_prev = datetime.strptime(area_admissions_date, '%d %B %Y') - timedelta(days=6)
    area_admissions_week_prev = obj_area_admissions_week_prev.strftime('%d %B %Y')
    obj_area_admissions_fortnight_prev = datetime.strptime(area_admissions_date, '%d %B %Y') - timedelta(days=13)
    area_admissions_fortnight_prev = obj_area_admissions_fortnight_prev.strftime('%d %B %Y')
    obj_area_admissions_prev_week_begin = datetime.strptime(area_admissions_date, '%d %B %Y') - timedelta(days=7)
    area_prev_admissions_week_begin = obj_area_admissions_prev_week_begin.strftime('%d %B %Y')
    
    obj_area_deaths_week_prev = datetime.strptime(area_deaths_date, '%d %B %Y') - timedelta(days=6)
    area_deaths_week_prev = obj_area_deaths_week_prev.strftime('%d %B %Y')
    obj_area_deaths_fortnight_prev = datetime.strptime(area_deaths_date, '%d %B %Y') - timedelta(days=13)
    area_deaths_fortnight_prev = obj_area_deaths_fortnight_prev.strftime('%d %B %Y')
    obj_area_deaths_prev_week_begin = datetime.strptime(area_deaths_date, '%d %B %Y') - timedelta(days=7)
    area_prev_deaths_week_begin = obj_area_deaths_prev_week_begin.strftime('%d %B %Y')


    area_week_cases_total, area_fortnight_cases_change, area_trial_cases_change = get_week(area_data, "newCasesByPublishDate")
    if isinstance(area_fortnight_cases_change, str):
        area_cases_arrow_colour = "red"
        area_cases_arrow_direction = ""
    elif area_fortnight_cases_change < 0:
        area_cases_arrow_colour = "green"
        area_cases_arrow_direction = "down"
    else:
        area_cases_arrow_colour = "red"
        area_cases_arrow_direction = "up"

    area_week_tests_total, area_fortnight_tests_change, area_trial_tests_change = get_week(area_data, "newTestsByPublishDate")

    if isinstance(area_fortnight_tests_change, str):
        area_tests_arrow_direction = ""
    elif area_fortnight_tests_change < 0:
        area_tests_arrow_direction = "down"
    else:
        area_tests_arrow_direction = "up"

    area_week_admissions_total, area_fortnight_admissions_change, area_trial_admissions_change = get_week(area_data, "newAdmissions")

    if isinstance(area_fortnight_admissions_change, str):
        area_admissions_arrow_colour = "red"
        area_admissions_arrow_direction = ""
    elif area_fortnight_admissions_change < 0:
        area_admissions_arrow_direction = "down"
        area_admissions_arrow_colour = "green"
    else:
        area_admissions_arrow_direction = "up"
        area_admissions_arrow_colour = "red"

    area_week_deaths_total, area_fortnight_deaths_change, area_trial_deaths_change = get_week(area_data, "newDeaths28DaysByPublishDate")

    if isinstance(area_fortnight_deaths_change, str):
        area_deaths_arrow_colour = "red"
        area_deaths_arrow_direction = ""
    elif fortnight_deaths_change < 0:
        area_deaths_arrow_direction = "down"
        area_deaths_arrow_colour = "green"
    else:
        area_deaths_arrow_direction = "up"
        area_deaths_arrow_colour = "red"


    


    return render_template(
        'main.html',
        areaname=area_name,
        areanewcases=area_new_cases,
        areanewtests=area_new_tests,
        areanewadmissions=area_new_admissions,
        areanewdeaths=area_new_deaths,
        areacasesdate=area_cases_date,
        areatestsdate=area_tests_date,
        areaadmissionsdate=area_admissions_date,
        areadeathsdate=area_deaths_date,
        areaweekofcases=area_week_cases_total,
        areaweekoftests=area_week_tests_total,
        areaweekofadmissions=area_week_admissions_total,
        areaweekofdeaths=area_week_deaths_total,
        areacaseschange=area_fortnight_cases_change,
        areatestschange=area_fortnight_tests_change,
        areaadmissionschange=area_fortnight_admissions_change,
        areadeathschange=area_fortnight_deaths_change,
        areacasestagcol=area_cases_arrow_colour,
        areaadmissionstagcol=area_admissions_arrow_colour,
        areadeathstagcol=area_deaths_arrow_colour,
        areacasesarrowdir=area_cases_arrow_direction,
        areatestsarrowdir=area_tests_arrow_direction,
        areaadmissionsarrowdir=area_admissions_arrow_direction,
        areadeathsarrowdir=area_deaths_arrow_direction,
        areacasestrialchange=area_trial_cases_change,
        
        areacasesdateprevweek=area_cases_week_prev,
        areacasesdateprevweekstart=area_prev_cases_week_begin,
        areacasesdatefortnightprev=area_cases_fortnight_prev,

        areatestsdateprevweek=area_tests_week_prev,
        areatestsdateprevweekstart=area_prev_tests_week_begin,
        areatestsdatefortnightprev=area_tests_fortnight_prev,

        areaadmissionsdateprevweek=area_admissions_week_prev,
        areaadmissionsdateprevweekstart=area_prev_admissions_week_begin,
        areaadmissionsdatefortnightprev=area_admissions_fortnight_prev,

        areadeathsdateprevweek=area_deaths_week_prev,
        areadeathsdateprevweekstart=area_prev_deaths_week_begin,
        areadeathsdatefortnightprev=area_deaths_fortnight_prev,

        newcases=new_cases,
        casesdate=cases_date,
        casesdateweekprev=cases_week_prev,
        casesdateprevweekstart=prev_cases_week_begin,
        casesdatefortnightprev=cases_fortnight_prev,

        newtests=new_tests,
        testsdate=tests_date,
        testsdateweekprev=tests_week_prev,
        testsdateprevweekstart=prev_tests_week_begin,
        testsdatefortnightprev=tests_fortnight_prev,

        newadmissions=new_admissions,
        admissionsdate=admissions_date,
        admissionsdateweekprev=admissions_week_prev,
        admissionsdateprevweekstart=prev_admissions_week_begin,
        admissionsdatefortnightprev=admissions_fortnight_prev,

        newdeaths=new_deaths,
        deathsdate=deaths_date,
        deathsdateweekprev=deaths_week_prev,
        deathsdateprevweekstart=prev_deaths_week_begin,
        deathsdatefortnightprev=deaths_fortnight_prev,
        
        weekofcases=week_cases_total,
        weekoftests=week_tests_total,
        weekofadmissions=week_admissions_total,
        weekofdeaths=week_deaths_total,
        caseschange=fortnight_cases_change,
        testschange=fortnight_tests_change,
        admissionschange=fortnight_admissions_change,
        deathschange=fortnight_deaths_change,
        casestagcol=cases_arrow_colour,
        admissionstagcol=admissions_arrow_colour,
        deathstagcol=deaths_arrow_colour,
        casesarrowdir=cases_arrow_direction,
        testsarrowdir=tests_arrow_direction,
        admissionsarrowdir=admissions_arrow_direction,
        deathsarrowdir=deaths_arrow_direction,
        casestrialchange=trial_cases_change,
        date=result_date,
        datefortnightprev=string_fortnight_prev,
        dateweekprev=string_week_prev
    )


# @app.route('/interactive-map')
# def statpage() -> render_template: 
#     return render_template(
#         "static.html",
#         data=data,
#         date=result_date,
#         newcases=new_cases,
#         casesdate=cases_date,
#         casesdateweekprev=cases_week_prev,
#         casesdateprevweekstart=prev_cases_week_begin,
#         casesdatefortnightprev=cases_fortnight_prev,
#         newtests=new_tests,
#         testsdate=tests_date,
#         testsdateweekprev=tests_week_prev,
#         testsdateprevweekstart=prev_tests_week_begin,
#         testsdatefortnightprev=tests_fortnight_prev,
#         newadmissions=new_admissions,
#         admissionsdate=admissions_date,
#         admissionsdateweekprev=admissions_week_prev,
#         admissionsdateprevweekstart=prev_admissions_week_begin,
#         admissionsdatefortnightprev=admissions_fortnight_prev,
#         newdeaths=new_deaths,
#         deathsdate=deaths_date,
#         deathsdateweekprev=deaths_week_prev,
#         deathsdateprevweekstart=prev_deaths_week_begin,
#         deathsdatefortnightprev=deaths_fortnight_prev,
#         weekofcases=week_cases_total,
#         weekoftests=week_tests_total,
#         weekofadmissions=week_admissions_total,
#         weekofdeaths=week_deaths_total,
#         caseschange=fortnight_cases_change,
#         testschange=fortnight_tests_change,
#         admissionschange=fortnight_admissions_change,
#         deathschange=fortnight_deaths_change,
#         casestagcol=cases_arrow_colour,
#         admissionstagcol=admissions_arrow_colour,
#         deathstagcol=deaths_arrow_colour,
#         casesarrowdir=cases_arrow_direction,
#         testsarrowdir=tests_arrow_direction,
#         admissionsarrowdir=admissions_arrow_direction,
#         deathsarrowdir=deaths_arrow_direction,
#         casestrialchange=trial_cases_change

#     )


@app.route('/', methods=['GET'])
@app.route('/<path>', methods=['GET'])
def index(path=None) -> render_template:
    return render_template(
        "main.html",
        data=data,
        date=result_date,
        newcases=new_cases,
        casesdate=cases_date,
        casesdateweekprev=cases_week_prev,
        casesdateprevweekstart=prev_cases_week_begin,
        casesdatefortnightprev=cases_fortnight_prev,

        newtests=new_tests,
        testsdate=tests_date,
        testsdateweekprev=tests_week_prev,
        testsdateprevweekstart=prev_tests_week_begin,
        testsdatefortnightprev=tests_fortnight_prev,

        newadmissions=new_admissions,
        admissionsdate=admissions_date,
        admissionsdateweekprev=admissions_week_prev,
        admissionsdateprevweekstart=prev_admissions_week_begin,
        admissionsdatefortnightprev=admissions_fortnight_prev,

        newdeaths=new_deaths,
        deathsdate=deaths_date,
        deathsdateweekprev=deaths_week_prev,
        deathsdateprevweekstart=prev_deaths_week_begin,
        deathsdatefortnightprev=deaths_fortnight_prev,

        weekofcases=week_cases_total,
        weekoftests=week_tests_total,
        weekofadmissions=week_admissions_total,
        weekofdeaths=week_deaths_total,
        caseschange=fortnight_cases_change,
        testschange=fortnight_tests_change,
        admissionschange=fortnight_admissions_change,
        deathschange=fortnight_deaths_change,
        casestagcol=cases_arrow_colour,
        admissionstagcol=admissions_arrow_colour,
        deathstagcol=deaths_arrow_colour,
        casesarrowdir=cases_arrow_direction,
        testsarrowdir=tests_arrow_direction,
        admissionsarrowdir=admissions_arrow_direction,
        deathsarrowdir=deaths_arrow_direction,
        casestrialchange=trial_cases_change,
        datefortnightprev=string_fortnight_prev,
        dateweekprev=string_week_prev
        # teststrialchange=trial_tests_change
    )


filters_overview = [
    'areaType=overview'
]

structure = {
    "date": "date",
    "areaName": "areaName",
    "newCasesByPublishDate": "newCasesByPublishDate",
    "newDeaths28DaysByPublishDate": "newDeaths28DaysByPublishDate",
    "cumTestsByPublishDate": "cumTestsByPublishDate",
    "newTestsByPublishDate": "newTestsByPublishDate",
    "newAdmissions": "newAdmissions",
    "newCasesBySpecimenDate": "newCasesBySpecimenDate"

}
#
# # get json data and seperate values into variables for parsing to template
api = Cov19API(
    filters=filters_overview,
    structure=structure
)


data = api.get_json()

# from .data.queries import get_last_fortnight
# data = [value for value in structure.values()]

obj_result_date = datetime.strptime(data["data"][0]["date"], '%Y-%m-%d')
result_date = obj_result_date.strftime('%d %B %Y')
obj_week_prev = datetime.strptime(data["data"][0]["date"], '%Y-%m-%d') - timedelta(days=6)
string_week_prev = obj_week_prev.strftime('%d %B %Y')
obj_fortnight_prev = datetime.strptime(data["data"][0]["date"], '%Y-%m-%d') - timedelta(days=13)
string_fortnight_prev = obj_fortnight_prev.strftime('%d %B %Y')


get_value = itemgetter("value")


def get_change(metric_data):
    mean_this_week = mean(map(get_value, metric_data[:7]))
    mean_one_week_ago = mean(map(get_value, metric_data[7:]))
    delta_mean = mean_this_week - mean_one_week_ago
    delta_percentage = delta_mean * 100 / mean_one_week_ago
    try:
        return {
            "percentage": format(delta_percentage, ".4g"),
            "value": "{:,}".format(float(format(delta_mean, ".4g")))
        }
    except ZeroDivisionError:
        return 0


def get_fortnight_data(area_name="United Kingdom"):
    metric_names = [
        "newCasesByPublishDate",
        "newDeaths28DaysByPublishDate",
        "newTestsByPublishDate",
        "newAdmissions"
    ]

    global timestamp

    result = dict()

    for metric in metric_names:
        metric_data = get_last_fortnight(timestamp, area_name, metric)

        result[metric] = {
            "data": metric_data,
            "change": get_change(metric_data),
        }

    return result


week_cases_total, fortnight_cases_change, trial_cases_change = get_week(data, "newCasesByPublishDate")
if isinstance(fortnight_cases_change, str):
    cases_arrow_colour = "red"
    cases_arrow_direction = ""
elif fortnight_cases_change < 0:
    cases_arrow_colour = "green"
    cases_arrow_direction = "down"
else:
    cases_arrow_colour = "red"
    cases_arrow_direction = "up"

week_tests_total, fortnight_tests_change, trial_tests_change = get_week(data, "newTestsByPublishDate")

if isinstance(fortnight_tests_change, str):
    tests_arrow_direction = ""
elif fortnight_tests_change < 0:
    tests_arrow_direction = "down"
else:
    tests_arrow_direction = "up"

week_admissions_total, fortnight_admissions_change, trial_admissions_change = get_week(data, "newAdmissions")

if isinstance(fortnight_admissions_change, str):
    admissions_arrow_colour = "red"
    admissions_arrow_direction = ""
elif fortnight_admissions_change < 0:
    admissions_arrow_direction = "down"
    admissions_arrow_colour = "green"
else:
    admissions_arrow_direction = "up"
    admissions_arrow_colour = "red"

week_deaths_total, fortnight_deaths_change, trial_deaths_change = get_week(data, "newDeaths28DaysByPublishDate")

if isinstance(fortnight_deaths_change, str):
    deaths_arrow_colour = "red"
    deaths_arrow_direction = ""
elif fortnight_deaths_change < 0:
    deaths_arrow_direction = "down"
    deaths_arrow_colour = "green"
else:
    deaths_arrow_direction = "up"
    deaths_arrow_colour = "red"

# sets variable to latest date, if no data is found, loop to latest available


# get latest date for data point, beginning of week prior, a week prior, and 2 weeks prior

new_cases = get_data(data, "newCasesByPublishDate")
cases_date = get_date(data, "newCasesByPublishDate")
obj_cases_week_prev = datetime.strptime(cases_date, '%d %B %Y') - timedelta(days=6)
cases_week_prev = obj_cases_week_prev.strftime('%d %B %Y')
obj_cases_fortnight_prev = datetime.strptime(cases_date, '%d %B %Y') - timedelta(days=13)
cases_fortnight_prev = obj_cases_fortnight_prev.strftime('%d %B %Y')
obj_cases_prev_week_begin = datetime.strptime(cases_date, '%d %B %Y') - timedelta(days=7)
prev_cases_week_begin = obj_cases_prev_week_begin.strftime('%d %B %Y')

new_tests = get_data(data, "newTestsByPublishDate")
tests_date = get_date(data, "newTestsByPublishDate")
obj_tests_week_prev = datetime.strptime(tests_date, '%d %B %Y') - timedelta(days=6)
tests_week_prev = obj_tests_week_prev.strftime('%d %B %Y')
obj_tests_fortnight_prev = datetime.strptime(tests_date, '%d %B %Y') - timedelta(days=13)
tests_fortnight_prev = obj_tests_fortnight_prev.strftime('%d %B %Y')
obj_tests_prev_week_begin = datetime.strptime(tests_date, '%d %B %Y') - timedelta(days=7)
prev_tests_week_begin = obj_tests_prev_week_begin.strftime('%d %B %Y')

new_admissions = get_data(data, "newAdmissions")
admissions_date = get_date(data, "newAdmissions")
obj_admissions_week_prev = datetime.strptime(admissions_date, '%d %B %Y') - timedelta(days=6)
admissions_week_prev = obj_admissions_week_prev.strftime('%d %B %Y')
obj_admissions_fortnight_prev = datetime.strptime(admissions_date, '%d %B %Y') - timedelta(days=13)
admissions_fortnight_prev = obj_admissions_fortnight_prev.strftime('%d %B %Y')
obj_admissions_prev_week_begin = datetime.strptime(admissions_date, '%d %B %Y') - timedelta(days=7)
prev_admissions_week_begin = obj_admissions_prev_week_begin.strftime('%d %B %Y')

new_deaths = get_data(data, "newDeaths28DaysByPublishDate")
deaths_date = get_date(data, "newDeaths28DaysByPublishDate")
obj_deaths_week_prev = datetime.strptime(deaths_date, '%d %B %Y') - timedelta(days=6)
deaths_week_prev = obj_deaths_week_prev.strftime('%d %B %Y')
obj_deaths_fortnight_prev = datetime.strptime(deaths_date, '%d %B %Y') - timedelta(days=13)
deaths_fortnight_prev = obj_deaths_fortnight_prev.strftime('%d %B %Y')
obj_deaths_prev_week_begin = datetime.strptime(deaths_date, '%d %B %Y') - timedelta(days=7)
prev_deaths_week_begin = obj_deaths_prev_week_begin.strftime('%d %B %Y')


def main(req: HttpRequest, context: Context, latestPublished: str) -> HttpResponse:
    logging.info(req.url)

    global timestamp
    timestamp = latestPublished

    logging.info(dumps(get_fortnight_data(), indent=4))

    application = WsgiMiddleware(app)
    # context.timestamp =
    return application.main(req, context)
