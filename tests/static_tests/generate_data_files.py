#  this is for generating new data files in case of changes to data format

import json
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import datetime


from app import app, inject_timestamps_tests
from tests.utils import website_timestamp, timestamp, read_dict_file
from app.common.utils import get_card_data, get_fortnight_data, get_og_image_names
from app.common.data import variables


def generate_fortnight_and_metric_data(selection=None):
    #  requires returning result, metric_data in common/utils.py
    fortnight_data, metric_data = get_fortnight_data(timestamp)

    if selection == "metric":
        metric_data = str(metric_data)
        metric_data = metric_data.strip('[]')
        metric_data = metric_data.replace('}, ', '}\n')
        print(metric_data)
        with open('met_data.txt', 'w') as datafile:
            datafile.write(metric_data)
    
    elif selection == "fortnight":
        with open('fort_data', 'w') as datafile:
            datafile.write(fortnight_data)

    else:
        metric_data = str(metric_data)
        metric_data = metric_data.strip('[]')
        metric_data = metric_data.replace('},', '}\n')
        print(metric_data)
        with open('met_data.txt', 'w') as datafile:
            datafile.write(metric_data)
        
        with open('fort_data', 'w') as datafile:
            datafile.write(fortnight_data)

#generate_fortnight_and_metric_data("metric")
