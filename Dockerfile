FROM python:3.8.6-slim-buster

ENV PYTHONUNBUFFERED 1

WORKDIR /opt/www/

COPY ./database ./database
COPY ./storage ./storage
COPY ./app ./app
COPY ./requirements.txt ./requirements.txt
RUN python3 -m pip install --no-cache-dir -U pip                               && \
    python3 -m pip install --no-cache-dir setuptools                           && \
    python3 -m pip install -U --no-cache-dir -r /opt/www/requirements.txt      && \
    rm requirements.txt

EXPOSE 5000
