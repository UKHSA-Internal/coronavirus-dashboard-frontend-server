import unittest
from flask import g, request
from tqdm import tqdm as progress_bar

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from .utils import website_timestamp, timestamp, output_object_to_file, output_content_to_file
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
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                for postcode in progress_bar(postcodes, desc='Postcode Response Status'):
                    response = c.get(f'/search?postcode={postcode}')
                    # output_content_to_file("justresp.txt", response.data)
                    self.assertEqual(response.status_code, 200)
                    assert request.args['postcode'] == postcode

    def test_postcode_found(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                for postcode in progress_bar(postcodes, desc='Postcode Found Progress'):
                    response = c.get(f'/search?postcode={postcode}')
                    data = response.data
                    postcode = postcode.encode('UTF-8')
                    assert postcode in data

    def test_invalid_postcode(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp):
            with app.test_client() as c:
                for postcode in progress_bar(invalid_postcodes, desc='Invalid Postcode Test'):
                    response = c.get(f'/search?postcode={postcode}')
                    data = response.data
                    invalid_check = b'Invalid postcode'
                    assert invalid_check in data


if __name__ == "__main__":
    unittest.main()
