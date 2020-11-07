FROM tiangolo/uwsgi-nginx-flask:python3.8

ENV UWSGI_INI /app/uwsgi.ini
ENV STATIC_URL /app/app/static
ENV LISTEN_PORT 5000
ENV NGINX_WORKER_PROCESSES auto
ENV NGINX_WORKER_CONNECTIONS 1024
ENV NGINX_WORKER_OPEN_FILES 1024

ENV UWSGI_CHEAPER 50
ENV UWSGI_PROCESSES 51

COPY ./database         /app/database
COPY ./storage          /app/storage
COPY ./uwsgi.ini        /app/uwsgi.ini
COPY ./app              /app/app
COPY ./requirements.txt /app/requirements.txt

RUN python3 -m pip install --no-cache-dir -U pip                      && \
    python3 -m pip install --no-cache-dir setuptools                  && \
    python3 -m pip install -U --no-cache-dir -r /app/requirements.txt && \
    rm /app/requirements.txt

EXPOSE 5000
