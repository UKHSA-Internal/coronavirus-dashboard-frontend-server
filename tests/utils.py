import logging
import unittest
from flask import g
import requests
import json
import csv
import math
import urllib3
import datetime
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

http = urllib3.PoolManager()

website_timestamp = http.request('GET', 'https://coronavirus.data.gov.uk/public/assets/dispatch/website_timestamp').data.decode('ascii')

# get release timestamp from file, if date is old fetch the latest from the API
with open("../timefile.txt", 'r' ) as f:
    timestamp = f.read()

timestamp_obj = datetime.datetime.strptime(timestamp[:10], "%Y-%m-%d")

if datetime.datetime.now().replace(hour=0, minute= 0, second=0, microsecond=0) - datetime.timedelta(days=1) > timestamp_obj:
    json_timestamp = json.loads(http.request('GET','https://api.coronavirus.data.gov.uk/v2/data?areaType=overview&metric=releaseTimestamp').data.decode())
    timestamp = json_timestamp["body"][0]["releaseTimestamp"]
    with open("timefile.txt", "w") as f:
        f.write(timestamp)


# get all dates between and inclusive of the specified start and end date
def get_date_range(start_date: str, end_date: str) -> list:
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    result = []
    step = datetime.timedelta(days=1)
    while start <= end:
        result.append(datetime.datetime.strftime(start, "%Y-%m-%d"))
        start += step
    return result

# return postcode area as specified
def get_postcode_area_code(postcode : str, area_type : str):
    postcode_data = json.loads(http.request('GET', f'https://api.coronavirus.data.gov.uk/v1/code?category=postcode&search={postcode}').data.decode())
    
    # if there's no area_type for the specified NHS region (E.g. areas outside of England) return nation instead
    if postcode_data[area_type] == None and area_type == "nhsRegion":
        return postcode_data["nation"]
    else:
        return postcode_data[area_type]

def get_area_data(metric: str, area_type: str, postcode: str):
    if area_type == "UK":
        data = json.loads(http.request('GET', f'https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=overview&structure=%7B%22{metric}%22:%22{metric}%22,%22date%22:%22date%22%7D').data.decode())
    else:
        # if deaths metric in wales or NI  use national
        area_code = get_postcode_area_code(postcode, area_type)
        if (area_code[:1] == 'W' or area_code[:1] == 'N') and metric == "newDeaths28DaysByPublishDate":
            area_code = get_postcode_area_code(postcode, "nation")
            area_type = "nation"
        # if the area code isn't England use national data instead of nhsRegions
        elif area_code[:1] != 'E' and area_type == "nhsRegion":
            area_type = "nation"
        data = json.loads(http.request('GET', f'https://api.coronavirus.data.gov.uk/v1/data?filters=areaType={area_type};areaCode={area_code}&structure=%7B%22{metric}%22:%22{metric}%22,%22date%22:%22date%22%7D').data.decode())

    return data


def calculate_dates(data):
    
    str_latest_date = data["data"][0]["date"]
    latest_date = datetime.datetime.strptime(str_latest_date, "%Y-%m-%d")

    current_week_date = datetime.date.strftime(latest_date - datetime.timedelta(days=6), "%Y-%m-%d")
    latest_week_ago_date = datetime.date.strftime(latest_date - datetime.timedelta(days=7), "%Y-%m-%d")
    date_fortnight_prior = datetime.date.strftime(latest_date - datetime.timedelta(days=13), "%Y-%m-%d")
   
    date_range_last_7 = get_date_range(current_week_date, str_latest_date)
    date_range_prev_7 = get_date_range(date_fortnight_prior, latest_week_ago_date)


    return  [str_latest_date, latest_date, current_week_date, latest_week_ago_date, date_fortnight_prior, date_range_last_7, date_range_prev_7]


# calculating the difference between previous 7 days and the 7 prior to that 
def calculate_change(metric: str, area_type: str = "UK", postcode: str = "") -> tuple:
    prev_week_count = 0
    latest_week_count = 0

    data = get_area_data(metric, area_type, postcode)
    
    dates = calculate_dates(data)

    date_range_last_7 = dates[5]
    date_range_prev_7 = dates[6]

    for item in data["data"]:
        if item["date"] in date_range_prev_7:
            prev_week_count += item[metric]
             
    for item in data["data"]:
        if item["date"] in date_range_last_7:
            latest_week_count += item[metric]

    change = latest_week_count - prev_week_count
    
    try:
        percentage_change = (change / prev_week_count) * 100
    except ZeroDivisionError:
        if change == 1:
            percentage_change = change * 100
        else:
            percentage_change = change * 100
    
    percentage_change = "{0:0.1f}".format(percentage_change)
    
    
    if change == 0:
        return ("No change", "No change")
    else:
        return(str(f'{change:,}'), str(percentage_change))

# get the first and last date of relevant date ranges

def get_date_min_max(metric: str, area_type: str = "UK", postcode: str = " ") -> tuple:
    data = get_area_data(metric, area_type, postcode)
    dates = calculate_dates(data)    

    for index, current_date in enumerate(dates):
        if index != 1 and index < 5:
            current_date = datetime.datetime.strptime(current_date, "%Y-%m-%d")
            dates[index] = datetime.datetime.strftime(current_date, "%d %B %Y").lstrip("0")

    
    latest_date = dates[0]
    current_week_date = dates[2]

    latest_week_ago_date = dates[3]
    date_fortnight_prior = dates[4]

    return latest_date, current_week_date, latest_week_ago_date, date_fortnight_prior

def read_dict_file(file: str):
    output = []
    
    with open(file, "r") as f:
        for line in f:
            line = line.rstrip()
            dictobj = eval(line)
            output.append(dictobj)

    return output