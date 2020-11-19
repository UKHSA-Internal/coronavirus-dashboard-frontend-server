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

    def test_response_status(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/')
            self.assertEqual(response.status_code, 200)

    def test_metric_change(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/')
            data = response.data
            cases_change, cases_percentage_change = calculate_change("newCasesByPublishDate")
            deaths_change, deaths_percentage_change = calculate_change("newDeaths28DaysByPublishDate")
            admissions_change, admissions_percentage_change = calculate_change("newAdmissions")
            tests_change, tests_percentage_change = calculate_change("newPCRTestsByPublishDate")
            self.assertIn(cases_change.encode(), data)
            self.assertIn(deaths_change.encode(), data)
            self.assertIn(admissions_change.encode(), data)
            self.assertIn(tests_change.encode(), data)

    def test_percentage_change(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/')
            data = response.data
            cases_change, cases_percentage_change = calculate_change("newCasesByPublishDate")
            deaths_change, deaths_percentage_change = calculate_change("newDeaths28DaysByPublishDate")
            admissions_change, admissions_percentage_change = calculate_change("newAdmissions")
            tests_change, tests_percentage_change = calculate_change("newPCRTestsByPublishDate")

            self.assertIn(cases_percentage_change.encode(), data)
            self.assertIn(deaths_percentage_change.encode(), data)
            self.assertIn(admissions_percentage_change.encode(), data)
            self.assertIn(tests_percentage_change.encode(), data)
    
    def test_date_range(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/')

        data = response.data
        cases_latest_date, cases_current_week_date, cases_latest_week_ago_date, cases_date_fortnight_prior = get_date_min_max("newCasesByPublishDate")
        deaths_latest_date, deaths_current_week_date, deaths_latest_week_ago_date, deaths_date_fortnight_prior = get_date_min_max("newDeaths28DaysByPublishDate")
        admissions_latest_date, admissions_current_week_date, admissions_latest_week_ago_date, admissions_date_fortnight_prior = get_date_min_max("newAdmissions")
        tests_latest_date, tests_current_week_date, tests_latest_week_ago_date, tests_date_fortnight_prior = get_date_min_max("newDeaths28DaysByPublishDate")

        self.assertIn(cases_latest_date.encode(), data), self.assertIn(cases_current_week_date.encode(), data), self.assertIn(cases_latest_week_ago_date.encode(), data), self.assertIn(cases_date_fortnight_prior.encode(), data)
        self.assertIn(deaths_latest_date.encode(), data), self.assertIn(deaths_current_week_date.encode(), data), self.assertIn(deaths_latest_week_ago_date.encode(), data), self.assertIn(deaths_date_fortnight_prior.encode(), data)
        self.assertIn(admissions_latest_date.encode(), data), self.assertIn(admissions_current_week_date.encode(), data), self.assertIn(admissions_latest_week_ago_date.encode(), data), self.assertIn(admissions_date_fortnight_prior.encode(), data)
        self.assertIn(tests_latest_date.encode(), data), self.assertIn(tests_current_week_date.encode(), data), self.assertIn(tests_latest_week_ago_date.encode(), data), self.assertIn(tests_date_fortnight_prior.encode(), data)


if __name__ == "__main__":
    unittest.main()
