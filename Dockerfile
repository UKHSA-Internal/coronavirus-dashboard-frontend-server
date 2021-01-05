FROM node:14-buster-slim AS builder
LABEL maintainer="Pouria Hadjibagheri <Pouria.Hadjibagheri@phe.gov.uk>"

WORKDIR /app/static

COPY ./app/static  /app/static

RUN rm -rf node_modules
RUN npm install
RUN npm rebuild node-sass
RUN npm run build /app/static
RUN rm -rf node_modules


FROM tiangolo/uwsgi-nginx-flask:python3.8
LABEL maintainer="Pouria Hadjibagheri <Pouria.Hadjibagheri@phe.gov.uk>"

ENV UWSGI_INI /app/uwsgi.ini

ENV UWSGI_CHEAPER 15
ENV UWSGI_PROCESSES 16

# Standard set up Nginx
WORKDIR /app

RUN apt-get update && apt-get upgrade -y --no-install-recommends

COPY --from=builder /app/static/dist ./static
COPY app/static/images               ./static/images
COPY app/static/icon                 ./static/icon
COPY app/static/govuk-frontend       ./static/govuk-frontend

COPY server/base.nginx               ./nginx.conf
COPY server/upload.nginx              /etc/nginx/conf.d/upload.conf
COPY server/engine.nginx              /etc/nginx/conf.d/engine.conf

COPY ./uwsgi.ini                     ./uwsgi.ini
COPY ./app                           ./app
COPY ./requirements.txt              ./requirements.txt

RUN python3 -m pip install --no-cache-dir -U pip                      && \
    python3 -m pip install --no-cache-dir setuptools                  && \
    python3 -m pip install -U --no-cache-dir -r ./requirements.txt    && \
    rm ./requirements.txt

EXPOSE 5000
