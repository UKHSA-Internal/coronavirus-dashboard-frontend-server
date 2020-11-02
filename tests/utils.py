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
timestamp = "2020-11-01T15:50:42.4511435Z"


def output_object_to_file(filename: str, data: object, write_type: str = 'w') -> None:
    f = open(filename, write_type)
    f.write(str(getmembers(data)))
    f.close()


def output_content_to_file(filename: str, data: object, write_type: str = 'w') -> None:
    f = open(filename, write_type)
    f.write(data.decode('UTF-8'))
    f.close()

def calculate_rate(metric, area="UK"):
    count = 0
    start_date = False
    data = json.loads(requests.get(f'https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=overview&structure=%7B%22{metric}%22:%22{metric}%22,%22date%22:%22date%22%7D').content.decode())
    latest_date = datetime.strptime(timestamp[:10], "%Y-%m-%d")

    if metric == "newAdmissions":
        latest_complete_date = date.strftime(latest_date - timedelta(days=4), "%Y-%m-%d")
        latest_complete_date_week_prior = date.strftime(latest_date - timedelta(days=10), "%Y-%m-%d")
    else:
        latest_complete_date = date.strftime(latest_date - timedelta(days=5), "%Y-%m-%d")
        latest_complete_date_week_prior = date.strftime(latest_date - timedelta(days=11), "%Y-%m-%d")
    
    if area == "UK":
        population = 66796807
    # else:
    #     populations = csv.reader(open('popestimates.csv'))
    #     for row in populations:
    #         if row[0] == 'K02000001':
    #             print (row[3])

    
    for item in data["data"]:
        if item["date"] == latest_complete_date or start_date:
            start_date = True
            count += item[metric]
        if item["date"] == latest_complete_date_week_prior:
            break

    rate = (count / population) * 100000
    formatted = "{0:0.1f}".format(rate)
    return formatted

