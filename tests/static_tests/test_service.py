import unittest
from flask import g

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from app import app, inject_timestamps_tests
from app.service import format_timestamp, as_datestamp

latest_timestamp = "2020-11-22T16:39:13.575774Z"

class TestService(unittest.TestCase):
    def setUp(self) -> None:
        app.config['TESTING'] = True
        app.config['DEBUG'] = False

    def tearDown(self):
        pass

    def test_format_timestamp(self):
        self.assertEqual(format_timestamp(latest_timestamp),"Sunday 22 November 2020 at 04:39pm")

    def test_as_datestamp(self):
        self.assertEqual(as_datestamp(latest_timestamp), "2020-11-22")
        

if __name__ == "__main__":
    unittest.main()