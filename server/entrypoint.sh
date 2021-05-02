#! /usr/bin/env sh
set -e

# If there's a prestart.sh script in the /app directory, run it before starting
#PRE_START_PATH=/opt/prestart.sh
#echo "Checking for script in $PRE_START_PATH"
#if [ -f $PRE_START_PATH ] ; then
#    echo "Running script $PRE_START_PATH"
#    . $PRE_START_PATH
#else
#    echo "There is no script $PRE_START_PATH"
#fi

#exec uvicorn app.main:app --host 0.0.0.0 \
#                          --port 5100 \
#                          --workers 8 \
#                          --loop uvloop \
#                          --proxy-headers \
#                          --interface asgi3 \
#                          --backlog 16 \
#                          --timeout-keep-alive 10 \
#                          --limit-max-requests 16 \
#                          --http httptools

#exec nginx
#exec gunicorn -k app.uvicorn_worker.ServerUvicornWorker -c /opt/gunicorn_conf.py app.main:app

# Start Supervisor, with Nginx and ASGI
exec /usr/bin/supervisord -c /opt/supervisor/supervisord.conf
