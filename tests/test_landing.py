import unittest
from flask import g

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from .utils import website_timestamp, timestamp, calculate_change
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

    def test_response_status(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/')
            self.assertEqual(response.status_code, 200)

    def test_metric_change(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/')
            data = response.data
            cases_change = calculate_change("newCasesByPublishDate").encode()
            deaths_change = calculate_change("newDeaths28DaysByPublishDate").encode()
            admissions_change = calculate_change("newAdmissions").encode()
            tests_change = calculate_change("newPCRTestsByPublishDate").encode()
            self.assertIn(cases_change, data)
            self.assertIn(deaths_change, data)
            self.assertIn(admissions_change, data)
            self.assertIn(tests_change, data)
    

if __name__ == "__main__":
    unittest.main()
