#!/usr/bin python3


# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from os import getenv

# 3rd party:

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Config(object):
    TESTING = False
    DEBUG = False
    SECRET_KEY = getenv('FLASK_SECRET_KEY')
    APPLICATION_ROOT = "/"
