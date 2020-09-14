#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging

# 3rd party:
from flask import Flask, Response
from azure.functions import HttpRequest, HttpResponse, WsgiMiddleware, Context

# Internal:

try:
    from __app__.storage import StorageClient
except ImportError():
    from storage import StorageClient

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'main'
]


app = Flask(__name__)

app.config["APPLICATION_ROOT"] = "/"

storage_client = StorageClient(container='$web', path='index.html')
template_pointer = storage_client.download()
template = template_pointer.readall().decode()


@app.route('/', methods=["GET"])
@app.route('/<path>', methods=["GET"])
def hello_world(path=None):
    logging.info(f"Path: {path}")
    return Response(template, headers={'Cache-Control': 'public, max-age=300'})


def main(req: HttpRequest, context: Context) -> HttpResponse:
    logging.info(req.url)
    application = WsgiMiddleware(app)
    return application.main(req, context)
