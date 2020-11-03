from inspect import getmembers
import logging
import unittest
from flask import g
import requests
from datetime import datetime, timedelta, date
import json
import csv
import math

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


from app import app, inject_timestamps_tests

website_timestamp = requests.get('https://coronavirus.data.gov.uk/public/assets/dispatch/website_timestamp').content.decode('ascii')
timestamp = "2020-11-02T15:36:22.7274825Z"
timestamp_date = datetime.strptime(timestamp[:10], "%Y-%m-%d")
str_timestamp_date = datetime.strftime(timestamp_date, "%Y-%m-%d")

def output_object_to_file(filename: str, data: object, write_type: str = 'w') -> None:
    f = open(filename, write_type)
    f.write(str(getmembers(data)))
    f.close()


def output_content_to_file(filename: str, data: object, write_type: str = 'w') -> None:
    f = open(filename, write_type)
    f.write(data.decode('UTF-8'))
    f.close()


# get all dates between and inclusive of the specified start and end date
def get_date_range(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    result = []
    step = timedelta(days=1)
    while start <= end:
        result.append(datetime.strftime(start, "%Y-%m-%d"))
        start += step
    return result

# return postcode area as specified
def get_postcode_area_code(postcode : str, area_type : str):
    postcode_data = json.loads(requests.get(f'https://api.coronavirus.data.gov.uk/v1/code?category=postcode&search={postcode}').content.decode())
    
    # if there's no area_type for the specified NHS region (E.g. areas outside of England) return nation instead
    if postcode_data[area_type] == None and area_type == "nhsRegion":
        return postcode_data["nation"]
    else:
        return postcode_data[area_type]

# calculating the difference between previous 7 days and the 7 prior to that 
def calculate_change(metric, area_type: str = "UK", postcode: str = ""):
    prev_week_count = 0
    latest_week_count = 0
    
    if area_type == "UK":
        data = json.loads(requests.get(f'https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=overview&structure=%7B%22{metric}%22:%22{metric}%22,%22date%22:%22date%22%7D').content.decode())
    else:
        # if the area code isn't England use national data instead, if deaths metric in wales or NI also use national
        area_code = get_postcode_area_code(postcode, area_type)
        if (area_code[:1] == 'W' or area_code[:1] == 'N') and metric == "newDeaths28DaysByPublishDate":
            area_code = get_postcode_area_code(postcode, "nation")
            area_type = "nation"

        elif area_code[:1] != 'E' and area_type == "nhsRegion":
            area_type = "nation"
        data = json.loads(requests.get(f'https://api.coronavirus.data.gov.uk/v1/data?filters=areaType={area_type};areaCode={area_code}&structure=%7B%22{metric}%22:%22{metric}%22,%22date%22:%22date%22%7D').content.decode())

    str_latest_date = data["data"][0]["date"]
    latest_date = datetime.strptime(str_latest_date, "%Y-%m-%d")

    current_week_date = date.strftime(latest_date - timedelta(days=6), "%Y-%m-%d")
    latest_week_ago_date = date.strftime(latest_date - timedelta(days=7), "%Y-%m-%d")
    date_fortnight_prior = date.strftime(latest_date - timedelta(days=13), "%Y-%m-%d")
   
    date_range_last_7 = get_date_range(current_week_date, str_timestamp_date)
    date_range_prev_7 = get_date_range(date_fortnight_prior, latest_week_ago_date)
 
    for item in data["data"]:
        if item["date"] in date_range_prev_7:
            prev_week_count += item[metric]
             
    for item in data["data"]:
        if item["date"] in date_range_last_7:
            latest_week_count += item[metric]

    change = latest_week_count - prev_week_count
    if change == 0:
        return "No change"
    else:
        return(str(f'{change:,}'))
