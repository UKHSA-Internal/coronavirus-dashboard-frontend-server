import unittest
from flask import g

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from .utils import website_timestamp, timestamp, output_object_to_file, calculate_rate, calculate_change
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
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                response = c.get('/')
                # output_object_to_file("response.txt", response)
                self.assertEqual(response.status_code, 200)

    def test_cases_rate(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                response = c.get('/')
                data = response.data
                test_rate = calculate_rate("newCasesBySpecimenDate").encode('UTF-8')
                assert test_rate in data

    def test_deaths_rate(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                response = c.get('/')
                data = response.data
                test_rate = calculate_rate("newDeaths28DaysByDeathDate").encode('UTF-8')
                assert test_rate in data
    
    def test_admissions_rate(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                response = c.get('/')
                data = response.data
                test_rate = calculate_rate("newAdmissions").encode('UTF-8')
                assert test_rate in data

    def test_cases_change(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                response = c.get('/')
                data = response.data
                test_change = calculate_change("newCasesByPublishDate").encode('UTF-8')
                assert test_change in data
    
    def test_deaths_change(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                response = c.get('/')
                data = response.data
                test_change = calculate_change("newDeaths28DaysByPublishDate").encode('UTF-8')
                assert test_change in data

    def test_admissions_change(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                response = c.get('/')
                data = response.data
                test_change = calculate_change("newAdmissions").encode('UTF-8')
                assert test_change in data

    def test_tests_change(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                response = c.get('/')
                data = response.data
                test_change = calculate_change("newTestsByPublishDate").encode('UTF-8')
                assert test_change in data

if __name__ == "__main__":
    unittest.main()
