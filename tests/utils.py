from inspect import getmembers
import logging
import unittest
from flask import g
import requests
from datetime import datetime, timedelta, date
import json

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


from app import app, inject_timestamps_tests

website_timestamp = requests.get('https://coronavirus.data.gov.uk/public/assets/dispatch/website_timestamp').content.decode('ascii')
timestamp = "2020-10-29T15:39:48.6664795Z"


def output_object_to_file(filename: str, data: object, write_type: str = 'w') -> None:
    f = open(filename, write_type)
    f.write(str(getmembers(data)))
    f.close()


def output_content_to_file(filename: str, data: object, write_type: str = 'w') -> None:
    f = open(filename, write_type)
    f.write(data.decode('UTF-8'))
    f.close()

# def calculate_rate(metric= "newCasesBySpecimenDate", area="UK"):
#     data = json.loads(requests.get(f'https://api.coronavirus.data.gov.uk/v1/data?filters=areaType=overview&structure=%7B%22{metric}%22:%22{metric}%22,%22date%22:%22date%22%7D').content.decode())
#     latest_date = datetime.strptime(data["data"][0]["date"], "%Y-%m-%d")
#     latest_complete_date = date.strftime(latest_date - timedelta(days=5), "%Y-%m-%d")
#     if area == "UK":
#         population = 66796800
#     print(latest_complete_date)

# calculate_rate()
