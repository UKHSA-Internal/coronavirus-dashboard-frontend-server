import unittest
from flask import g, request
from tqdm import tqdm as progress_bar
import logging
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from ..utils import website_timestamp, timestamp, calculate_change, get_date_min_max
from app import app, inject_timestamps_tests
from app.common.data import variables

cases_metric = variables.DestinationMetrics["cases"]["metric"]
deaths_metric = variables.DestinationMetrics["deaths"]["metric"]
healthcare_metric = variables.DestinationMetrics["healthcare"]["metric"]
testing_metric = variables.DestinationMetrics["testing"]["metric"]


postcodes = [
    'CF101AE', 'AB101AU', 'BT11AA', 'CB12QX', 'TR210PP', 'TR96QP',
    'LU70BB', 'MK170DL', 'HP169PW', 'SG141AH', 'DA144HA', 'DA157HD', 'YO255HA',
    'MK183GZ', 'HP108AA', 'HP100JR', 'HP100AA', 'CA144AB', 'LE158NZ',
    'BB186JH', 'GL73HA', 'EC2N4AA'
]

invalid_postcodes = [
    'W1T6PJ', '111111', 'TK202NEEE', ' '
]

class TestPostcode(unittest.TestCase):
    def setUp(self) -> None:
        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        with app.app_context():
            g.timestamp = timestamp
            g.website_timestamp = website_timestamp

    def tearDown(self):
        pass

    def test_postcode_response_status(self):
        
        for postcode in progress_bar(postcodes, desc='Postcode Response Status'):
            with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
                response = client.get(f'/search?postcode={postcode}')
                self.assertEqual(request.args['postcode'], postcode)
            self.assertEqual(response.status_code, 200)
           
            

    def test_postcode_found(self):
        
        for postcode in progress_bar(postcodes, desc='Postcode Found Progress'):
            with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
                response = client.get(f'/search?postcode={postcode}')
            data = response.data
            postcode = postcode.encode('UTF-8')
            self.assertIn(postcode, data)

    def test_invalid_postcode(self):
        
        for postcode in progress_bar(invalid_postcodes, desc='Invalid Postcode Test'):
            with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
                response = client.get(f'/search?postcode={postcode}')
            data = response.data
            invalid_check = b'please enter a full and valid UK postcode'
            self.assertIn(invalid_check, data)

    def test_change(self):
        
        for postcode in progress_bar(postcodes, desc='Weekly change value check: '):
            with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
                response = client.get(f'/search?postcode={postcode}')
            
            data = response.data
            cases_change, cases_percentage_change = calculate_change(cases_metric, "ltla", postcode)
            deaths_change, deaths_percentage_change = calculate_change(deaths_metric, "ltla", postcode)
            admissions_change, admissions_percentage_change = calculate_change(healthcare_metric, "nhsTrust", postcode)
            tests_change, tests_percentage_change = calculate_change(testing_metric, "nation", postcode)

            self.assertIn(cases_change.encode(), data)
            self.assertIn(deaths_change.encode(), data)
            self.assertIn(admissions_change.encode(), data)
            self.assertIn(tests_change.encode(), data)

    def test_percentage_change(self):
        
        for postcode in progress_bar(postcodes, desc='Weekly percentage change value check: '):
            with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
                response = client.get(f'/search?postcode={postcode}')
            
            data = response.data
            cases_change, cases_percentage_change = calculate_change(cases_metric, "ltla", postcode)
            deaths_change, deaths_percentage_change = calculate_change(deaths_metric, "ltla", postcode)
            admissions_change, admissions_percentage_change = calculate_change(healthcare_metric, "nhsTrust", postcode)
            tests_change, tests_percentage_change = calculate_change(testing_metric, "nation", postcode)

            self.assertIn(cases_percentage_change.encode(), data)
            self.assertIn(deaths_percentage_change.encode(), data)
            self.assertIn(admissions_percentage_change.encode(), data)
            self.assertIn(tests_percentage_change.encode(), data)

    def test_date_range(self):
        for postcode in progress_bar(postcodes, desc='Check date ranges present:'):
            with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
                response = client.get(f'/search?postcode={postcode}')

            data = response.data
            cases_latest_date, cases_current_week_date, cases_latest_week_ago_date, cases_date_fortnight_prior = get_date_min_max(cases_metric, "ltla", postcode)
            deaths_latest_date, deaths_current_week_date, deaths_latest_week_ago_date, deaths_date_fortnight_prior = get_date_min_max(deaths_metric, "ltla", postcode)
            admissions_latest_date, admissions_current_week_date, admissions_latest_week_ago_date, admissions_date_fortnight_prior = get_date_min_max(healthcare_metric, "nhsTrust", postcode)
            tests_latest_date, tests_current_week_date, tests_latest_week_ago_date, tests_date_fortnight_prior = get_date_min_max(deaths_metric, "ltla", postcode)

            self.assertIn(cases_latest_date.encode(), data), self.assertIn(cases_current_week_date.encode(), data), self.assertIn(cases_latest_week_ago_date.encode(), data), self.assertIn(cases_date_fortnight_prior.encode(), data)
            #self.assertIn(deaths_latest_date.encode(), data), self.assertIn(deaths_current_week_date.encode(), data), self.assertIn(deaths_latest_week_ago_date.encode(), data), self.assertIn(deaths_date_fortnight_prior.encode(), data)
            self.assertIn(admissions_latest_date.encode(), data), self.assertIn(admissions_current_week_date.encode(), data), self.assertIn(admissions_latest_week_ago_date.encode(), data), self.assertIn(admissions_date_fortnight_prior.encode(), data)
            #self.assertIn(tests_latest_date.encode(), data), self.assertIn(tests_current_week_date.encode(), data), self.assertIn(tests_latest_week_ago_date.encode(), data), self.assertIn(tests_date_fortnight_prior.encode(), data)


if __name__ == "__main__":
    unittest.main()
