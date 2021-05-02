#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from dataclasses import dataclass
from os import getenv, path

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

dir_name = path.dirname(__file__)
templates_dir = path.join(dir_name, "templates")


@dataclass
class Settings:
    TESTING = getenv("IS_DEV", "0") == "1"
    DEBUG = getenv("IS_DEV", "0") == "1"
    template_path = templates_dir
    instrumentation_key = f'InstrumentationKey={getenv("APPINSIGHTS_INSTRUMENTATIONKEY", "")}'
    service_domain = getenv('URL_LOCATION', str())
    server_location = getenv('SERVER_LOCATION', "N/A")
    log_level = getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT = getenv("API_ENV")
    healthcheck_path = "healthcheck"
    cloud_role_name = getenv("WEBSITE_SITE_NAME", "landing-page")
    website_timestamp = {
        "container": "publicdata",
        "path":  "assets/dispatch/website_timestamp"
    }
    latest_published_timestamp = {
        "container": "pipeline",
        "path": "info/latest_published"
    }
    redis = dict(
        address=(getenv("AZURE_REDIS_HOST", ""), getenv("AZURE_REDIS_PORT", "")),
        password=getenv("AZURE_REDIS_PASSWORD"),
        maxsize=20
    )


class Config(object):
    TESTING = Settings.TESTING
    DEBUG = Settings.DEBUG
    SECRET_KEY = getenv('FLASK_SECRET_KEY')
    APPLICATION_ROOT = "/"
