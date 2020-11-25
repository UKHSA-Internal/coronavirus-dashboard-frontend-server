FROM node:14-buster-slim AS builder

WORKDIR /app/static

COPY ./app/static  /app/static

RUN rm -rf node_modules
RUN npm install
RUN npm rebuild node-sass
RUN npm run build /app/static
RUN rm -rf node_modules


FROM tiangolo/uwsgi-nginx-flask:python3.8

ENV UWSGI_INI /app/uwsgi.ini
ENV STATIC_URL /static
ENV STATIC_PATH /app/static
ENV LISTEN_PORT 5000
ENV NGINX_WORKER_PROCESSES auto
ENV NGINX_WORKER_CONNECTIONS 1024
ENV NGINX_WORKER_OPEN_FILES 1024

ENV UWSGI_CHEAPER 50
ENV UWSGI_PROCESSES 51

WORKDIR /app

COPY --from=builder /app/static/dist ./static

COPY ./database         ./database
COPY ./storage          ./storage
COPY ./uwsgi.ini        ./uwsgi.ini
COPY ./app              ./app
COPY ./requirements.txt ./requirements.txt

RUN apt-get update && apt-get install -y wget --no-install-recommends

RUN python3 -m pip install --no-cache-dir -U pip                      && \
    python3 -m pip install --no-cache-dir setuptools                  && \
    python3 -m pip install -U --no-cache-dir -r ./requirements.txt    && \
    rm ./requirements.txt

EXPOSE 5000
