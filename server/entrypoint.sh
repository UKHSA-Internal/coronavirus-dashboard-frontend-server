#! /usr/bin/env sh
set -e

# If there's a prestart.sh script in the /app directory, run it before starting
PRE_START_PATH=/opt/prestart.sh
echo "Checking for script in $PRE_START_PATH"
if [ -f $PRE_START_PATH ] ; then
    echo "Running script $PRE_START_PATH"
    . $PRE_START_PATH
else
    echo "There is no script $PRE_START_PATH"
fi

# Start Supervisor, with Nginx and ASGI
#exec /usr/bin/supervisord -c /opt/supervisor/supervisord.conf
exec uvicorn app.main:app --uds /opt/uvicorn.sock \
                          --workers 2 \
                          --loop uvloop \
                          --proxy-headers \
                          --host 0.0.0.0 \
                          --port 5100 \
                          --backlog 128 \
                          --timeout-keep-alive 10 \
                          --limit-max-requests 64 \
                          --http httptools
