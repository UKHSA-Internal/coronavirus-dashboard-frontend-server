import unittest
from flask import g
import json
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import datetime
import ast

#from ..utils import website_timestamp, timestamp
from app import app, inject_timestamps_tests

from app.common.utils import get_change

metric_data = []

with open("metric_data.txt","r") as f:

    for line in f:
        line = line.rstrip()
        dictobj = eval(line)
        print(dictobj)
        metric_data.append(dictobj)

    

class TestUtils(unittest.TestCase):
    def setUp(self) -> None:
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        # with app.app_context():
        #      g.timestamp = timestamp
        #      g.website_timestamp = website_timestamp

    def tearDown(self):
        pass

    def test_get_change(self):
        self.assertEqual(get_change(metric_data)["percentage"], '10.1')


    

if __name__ == "__main__":
    unittest.main()
