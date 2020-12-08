#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from os import getenv

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Config(object):
    TESTING = getenv("IS_DEV", "0") == "1"
    DEBUG = getenv("IS_DEV", "0") == "1"
    SECRET_KEY = getenv('FLASK_SECRET_KEY')
    APPLICATION_ROOT = "/"
