from inspect import getmembers
import logging
import unittest
from flask import g
import requests
from datetime import datetime, timedelta, date
import json
import csv

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

def get_date_range(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    result = []
    step = timedelta(days=1)
    while start <= end:
        result.append(datetime.strftime(start, "%Y-%m-%d"))
        start += step

    return result



def calculate_rate(metric, area: str = "UK"):
    count = 0
    data = json.loads(requests.get(f'https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=overview&structure=%7B%22{metric}%22:%22{metric}%22,%22date%22:%22date%22%7D').content.decode())
  
    if metric == "newAdmissions":
        latest_complete_date = date.strftime(timestamp_date - timedelta(days=4), "%Y-%m-%d")
        latest_complete_date_week_prior = date.strftime(timestamp_date - timedelta(days=10), "%Y-%m-%d")
        date_range = get_date_range(latest_complete_date_week_prior, latest_complete_date)
    else:
        latest_complete_date = date.strftime(timestamp_date - timedelta(days=5), "%Y-%m-%d")
        latest_complete_date_week_prior = date.strftime(timestamp_date - timedelta(days=11), "%Y-%m-%d")
        date_range = get_date_range(latest_complete_date_week_prior, latest_complete_date)
    
    if area == "UK":
        population = 66796807
    # else:
    #     populations = csv.reader(open('popestimates.csv'))
    #     for row in populations:
    #         if row[0] == 'K02000001':
    #             print (row[3])

    
    for item in data["data"]:
        if item["date"] in date_range:
            count += item[metric]

    rate = (count / population) * 100000
    formatted = "{0:0.1f}".format(rate)
    return str(formatted)


def calculate_change(metric, area: str = "UK"):
    prev_week_count = 0
    latest_week_count = 0
    data = json.loads(requests.get(f'https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=overview&structure=%7B%22{metric}%22:%22{metric}%22,%22date%22:%22date%22%7D').content.decode())
    
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
    return(str(f'{change:,}'))



