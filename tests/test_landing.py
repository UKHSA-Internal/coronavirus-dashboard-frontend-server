import unittest
from flask import g

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from .utils import website_timestamp, timestamp, output_object_to_file
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


if __name__ == "__main__":
    unittest.main()
