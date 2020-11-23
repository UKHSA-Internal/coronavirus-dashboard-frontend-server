import unittest
from flask import g
import json
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import datetime


from app import app, inject_timestamps_tests
from ..utils import website_timestamp, timestamp, read_dict_file
from app.common.utils import get_change, get_card_data

metric_data = read_dict_file("metric_data.txt")
    


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
        self.assertEqual(get_change(metric_data)["value"], 15947)
        self.assertEqual(get_change(metric_data)["trend"], 0)
        self.assertEqual(get_change(metric_data)["total"], 173616)

    def test_get_card_data(self):
        self.assertEqual(get_card_data("newPCRTestsByPublishDate", metric_data)["colour"], {'line': 'rgba(56,63,67,1)', 'fill': 'rgba(235,233,231,1)'})
        self.assertEqual(get_card_data("newPCRTestsByPublishDate", metric_data)["latest_date"], "18 November 2020")
    

if __name__ == "__main__":
    unittest.main()
