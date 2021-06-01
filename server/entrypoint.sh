#! /usr/bin/env sh
set -e

/usr/sbin/sshd
exec uvicorn app.main:app --workers 8                 \
                          --host 0.0.0.0              \
                          --loop uvloop               \
                          --port 5100                 \
                          --proxy-headers             \
                          --timeout-keep-alive 5      \
                          --backlog 32                \
                          --limit-concurrency 8

#exec gunicorn -k app.uvicorn_worker.ServerUvicornWorker -c /opt/gunicorn_conf.py app.main:app
