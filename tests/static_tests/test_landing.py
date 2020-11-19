import unittest
from flask import g

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from ..utils import website_timestamp, timestamp, calculate_change, get_date_min_max
from app import app, inject_timestamps_tests


class TestLanding(unittest.TestCase):
    def setUp(self) -> None:
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        with app.app_context():
            g.timestamp = timestamp
            g.website_timestamp = website_timestamp

    def tearDown(self):
        pass


    

if __name__ == "__main__":
    unittest.main()
