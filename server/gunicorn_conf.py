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

workers_per_core_str = getenv("WORKERS_PER_CORE", "1")
max_workers_str = getenv("MAX_WORKERS")
use_max_workers = None

if max_workers_str:
    use_max_workers = int(max_workers_str)

host = getenv("HOST", "0.0.0.0")
port = getenv("GUNICORN_PORT", "5100")

use_bind = getenv("BIND", f"{host}:{port}")

cores = cpu_count()
workers_per_core = float(workers_per_core_str)
default_web_concurrency = workers_per_core * cores + 1

web_concurrency = max(int(default_web_concurrency), 2)

graceful_timeout_str = getenv("GRACEFUL_TIMEOUT", "8")
timeout_str = getenv("TIMEOUT", "20")
keepalive_str = getenv("KEEP_ALIVE", "10")

# Gunicorn config variables
loglevel = 'info'
workers = web_concurrency
bind = use_bind
errorlog = "-"
worker_tmp_dir = "/dev/shm"
accesslog = "-"
graceful_timeout = int(graceful_timeout_str)
timeout = int(timeout_str)
keepalive = int(keepalive_str)
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
    # Additional, non-gunicorn variables
    "workers_per_core": workers_per_core,
    "use_max_workers": use_max_workers,
    "secure_scheme_headers": secure_scheme_headers,
    "proxy_protocol": proxy_protocol,
    "host": host,
    "port": port,
}

print(dumps(log_data))
