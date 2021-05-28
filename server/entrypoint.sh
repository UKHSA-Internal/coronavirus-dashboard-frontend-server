#! /usr/bin/env sh
set -e

exec gunicorn -k app.uvicorn_worker.ServerUvicornWorker -c /opt/gunicorn_conf.py app.main:app
