#!/usr/bin python3

"""
<Description of the programme>

Settings courtesy of ``tiangolo/uvicorn-gunicorn-docker``.

Author:        Pouria Hadjibagheri <pouria.hadjibagheri@phe.gov.uk>
Created:       22 Feb 2021
License:       MIT
Contributors:  Pouria Hadjibagheri
"""

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from json import dumps
from multiprocessing import cpu_count
from os import getenv

# 3rd party:

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Header
__author__ = "Pouria Hadjibagheri"
__copyright__ = "Copyright (c) 2021, Public Health England"
__license__ = "MIT"
__version__ = "0.0.1"
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

use_max_workers = 2

# web_concurrency_str = getenv("WEB_CONCURRENCY", None)

# cores = cpu_count()
# workers_per_core = 2
# default_web_concurrency = workers_per_core * cores
#
#
# if web_concurrency_str:
#     web_concurrency = int(web_concurrency_str)
#     assert web_concurrency > 0
# else:
#     web_concurrency = max(int(default_web_concurrency), 2)
#
#     if use_max_workers:
#         web_concurrency = min(web_concurrency, use_max_workers)


accesslog_var = getenv("ACCESS_LOG", "-")
use_accesslog = accesslog_var or None
errorlog_var = getenv("ERROR_LOG", "-")
use_errorlog = errorlog_var or None
graceful_timeout_str = getenv("GRACEFUL_TIMEOUT", "30")
timeout_str = getenv("TIMEOUT", "120")
keepalive_str = getenv("KEEP_ALIVE", "5")

# Gunicorn config variables
loglevel = 'INFO'
workers = 1
threads = 2
host = "0.0.0.0"
port = "5200"
max_requests = 10
bind = "0.0.0.0:5100"
# bind = "unix:///opt/server.sock"
errorlog = use_errorlog
worker_tmp_dir = "/dev/shm"
accesslog = use_accesslog
graceful_timeout = 20
timeout = 30
keepalive = 20
proxy_protocol = True
secure_scheme_headers = {
    'X-FORWARDED-PROTO': 'https'
}


# For debugging and testing
log_data = {
    "loglevel": loglevel,
    "workers": workers,
    "bind": bind,
    "graceful_timeout": graceful_timeout,
    "timeout": timeout,
    "keepalive": keepalive,
    "errorlog": errorlog,
    "accesslog": accesslog,
    # Additional, non-gunicorn variables
    # "workers_per_core": workers_per_core,
    "use_max_workers": use_max_workers,
    "secure_scheme_headers": secure_scheme_headers,
    "proxy_protocol": proxy_protocol,
    "host": host,
    "port": port,
}

print(dumps(log_data))
