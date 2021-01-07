import unittest
from flask import g
import json
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import datetime


from app import app, inject_timestamps_tests
from ..utils import read_dict_file
from app.common.utils import get_card_data, get_og_image_names
from app.common.data import variables

# cases_metric = variables.DestinationMetrics["cases"]["metric"]
# deaths_metric = variables.DestinationMetrics["deaths"]["metric"]
# healthcare_metric = variables.DestinationMetrics["healthcare"]["metric"]
# testing_metric = variables.DestinationMetrics["testing"]["metric"]

timestamp = "2021-01-04T20:45:36.8511875Z"

metric_data = read_dict_file("met_data.txt")
    


class TestUtils(unittest.TestCase):
    def setUp(self) -> None:
        app.config['TESTING'] = True
        app.config['DEBUG'] = False

    def tearDown(self):
        pass


    def test_get_card_data(self):
        # using same methods without DB calls
        self.assertEqual(metric_data[0]["date"].strftime('%-d %B %Y'), "4 January 2021")
    
    def test_get_og_names(self):
        self.assertEqual(get_og_image_names(timestamp),['/downloads/og-images/og-summary_20210104.png', '/downloads/og-images/og-newCasesByPublishDate_20210104.png', '/downloads/og-images/og-newDeaths28DaysByPublishDate_20210104.png', '/downloads/og-images/og-newAdmissions_20210104.png', '/downloads/og-images/og-newVirusTests_20210104.png']
)
if __name__ == "__main__":
    unittest.main()
