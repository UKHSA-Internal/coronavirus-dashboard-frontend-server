#!/usr/bin python3

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from os import getenv

# 3rd party:
import certifi
from flask_caching import Cache

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'cache_client'
]


ENVIRONMENT = getenv("API_ENV", "PRODUCTION")

server_location = {
    "PRODUCTION": getenv("SERVER_LOCATION", "UKS"),
    "STAGING": "UKS",
    "DEVELOPMENT": "UKS",
}


cache_client = Cache(config={
    "CACHE_TYPE": "redis",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "frontend::",
    "CACHE_OPTIONS": {
        "ssl": True,
        "ssl_ca_certs": certifi.where()
    },
    "CACHE_REDIS_HOST": getenv(f"{server_location[ENVIRONMENT]}_REDIS_HOST"),
    "CACHE_REDIS_PORT": int(getenv(f"{server_location[ENVIRONMENT]}_REDIS_PORT")),
    "CACHE_REDIS_PASSWORD": getenv(f"{server_location[ENVIRONMENT]}_REDIS_PASSWORD"),
    "CACHE_REDIS_DB": 0
})
