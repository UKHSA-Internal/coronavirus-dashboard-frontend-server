import unittest
from flask import g, request
from tqdm import tqdm as progress_bar
import logging
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from .utils import website_timestamp, timestamp, calculate_change
from app import app, inject_timestamps_tests

postcodes = [
    'CF101AE', 'AB101AU', 'BT11AA', 'CB12QX', 'TR210PP', 'TR96QP',
    'LU70BB', 'MK170DL', 'HP169PW', 'SG141AH', 'DA144HA', 'DA157HD', 'YO255HA',
    'MK183GZ', 'HP108AA', 'HP100JR', 'HP100AA', 'CA144AB', 'LE158NZ',
    'BB186JH', 'GL73HA', 'EC2N4AA'
]

invalid_postcodes = [
    'W1T6PJ', '111111', 'TK202NEEE', ' '
]


class TestLanding(unittest.TestCase):
    def setUp(self) -> None:
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        with app.app_context():
            g.timestamp = timestamp
            g.website_timestamp = website_timestamp

    def tearDown(self):
        pass

    def test_postcode_response_status(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            for postcode in progress_bar(postcodes, desc='Postcode Response Status'):
                response = client.get(f'/search?postcode={postcode}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(request.args['postcode'], postcode)

    def test_postcode_found(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            for postcode in progress_bar(postcodes, desc='Postcode Found Progress'):
                response = client.get(f'/search?postcode={postcode}')
                data = response.data
                postcode = postcode.encode('UTF-8')
                self.assertIn(postcode, data)

    def test_invalid_postcode(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            for postcode in progress_bar(invalid_postcodes, desc='Invalid Postcode Test'):
                response = client.get(f'/search?postcode={postcode}')
                data = response.data
                invalid_check = b'Invalid postcode'
                self.assertIn(invalid_check, data)

    def test_change(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            
            for postcode in progress_bar(postcodes, desc='Weekly change value check: '):
                response = client.get(f'/search?postcode={postcode}')
                data = response.data

                cases_change = calculate_change("newCasesByPublishDate", "ltla", postcode).encode()
                deaths_change = calculate_change("newDeaths28DaysByPublishDate", "ltla", postcode).encode()
                admissions_change = calculate_change("newAdmissions", "nhsRegion", postcode).encode()
                tests_change = calculate_change("newPCRTestsByPublishDate", "nation", postcode).encode()

                self.assertIn(cases_change, data)
                self.assertIn(deaths_change, data)
                self.assertIn(admissions_change, data)
                self.assertIn(tests_change, data)
    


if __name__ == "__main__":
    unittest.main()
