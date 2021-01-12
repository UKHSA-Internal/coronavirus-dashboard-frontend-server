import unittest
from flask import g

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from ..utils import website_timestamp, timestamp, get_postcode_area_code
from app import app, inject_timestamps_tests


class PostcodeMappingCheck(unittest.TestCase):
    def setUp(self) -> None:
        app.config['TESTING'] = True
        app.config['DEBUG'] = False
        with app.app_context():
            g.timestamp = timestamp
            g.website_timestamp = website_timestamp

    def tearDown(self):
        pass
    
    def test_MSOA_names(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=DA144HA')

        data = response.data
        self.assertIn(b'Sidcup East', data)

        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=DA157HD')

        data = response.data
        self.assertIn(b'Sidcup West', data)

    def test_LTLA_names(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=CA144AB')

        data = response.data
        self.assertIn(b'Copeland', data)

        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=LE158NZ')

        data = response.data
        self.assertIn(b'East Northamptonshire', data)

        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=BB186JH')

        data = response.data
        self.assertIn(b'Pendle', data)

        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=GL73HA')

        data = response.data
        self.assertIn(b'Vale of White Horse', data)


    def test_nhs_region(self):
        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=LU70BB')

        data = response.data
        self.assertIn(b'East of England', data)
        self.assertIn(b'Aylesbury Vale', data)

        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=MK170DL')

        data = response.data
        self.assertIn(b'East of England', data)
        self.assertIn(b'Aylesbury Vale', data)

        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=HP169PW')

        data = response.data
        self.assertIn(b'South East', data)
        self.assertIn(b'Aylesbury Vale', data)

        with inject_timestamps_tests(app, timestamp, website_timestamp), app.test_client() as client:
            response = client.get('/search?postcode=MK183GZ')

        data = response.data
        self.assertIn(b'South East', data)
        self.assertIn(b'Aylesbury Vale', data)
            

if __name__ == "__main__":
    unittest.main()
