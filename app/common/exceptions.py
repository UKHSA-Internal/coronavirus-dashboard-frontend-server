#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:

# 3rd party:
from werkzeug.exceptions import HTTPException
from flask import render_template, Response

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'InvalidPostcode',
    'HandledException'
]


class HandledException(object):
    template = None
    template_kws = dict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_body(self, environ=None):
        return render_template(self.template, **self.template_kws)


class InvalidPostcode(HandledException, HTTPException):
    code = 400
    message_template = 'Invalid postcode: "{postcode}"'
    template = "main.html"

    def __init__(self, postcode):
        self.postcode = postcode
        self.template_kws = {
            'invalid_postcode': True,
            'message': self.message
        }
        super().__init__(description=self.message)

    @property
    def message(self):
        return self.message_template.format(postcode=self.postcode)

