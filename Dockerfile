FROM node:14-buster-slim AS builder
LABEL maintainer="Pouria Hadjibagheri <Pouria.Hadjibagheri@phe.gov.uk>"

WORKDIR /app/static

COPY ./app/assets                     /app/static

RUN rm -rf node_modules
RUN npm install
RUN npm rebuild node-sass
RUN npm run build /app/static
RUN rm -rf node_modules

FROM python:3.9-buster

ENV NUMEXPR_MAX_THREADS   1

COPY server/install-nginx.sh          /install-nginx.sh
RUN bash /install-nginx.sh
RUN rm /etc/nginx/conf.d/default.conf

# Install Supervisord
RUN apt-get update                                    && \
    apt-get upgrade -y --no-install-recommends        && \
    apt-get install -y supervisor openssh-server      && \
    echo "root:Docker!" | chpasswd                    && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt

COPY requirements.txt       ./config/requirements.txt

RUN apt update                                                   && \
    pip3 install -r /opt/config/requirements.txt                 && \
    apt remove -y python3-pip                                    && \
    apt autoremove --purge -y                                    && \
    rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list   && \
    rm -rf /opt/config/requirements.txt


COPY --from=builder /app/static/dist             /opt/assets
COPY app/assets/images                           /opt/assets/images
COPY app/assets/icon                             /opt/assets/icon
COPY app/assets/govuk-frontend                   /opt/assets/govuk-frontend
COPY app/assets/images/opengraph-image.png       /opt/assets/public/images/opengraph-image.png
COPY ./app                                       /opt/app

# Gunicorn config
COPY server/gunicorn_conf.py          /opt/gunicorn_conf.py

COPY server/supervisord.conf          /opt/supervisor/supervisord.conf

# Main service entrypoint - launches supervisord
COPY server/start-gunicorn.sh             /opt/start-gunicorn.sh
COPY server/entrypoint.sh             /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh
RUN chmod +x /opt/start-gunicorn.sh

COPY server/base.nginx                /etc/nginx/nginx.conf
COPY server/engine.nginx              /etc/nginx/conf.d/engine.conf

RUN mkdir -p /opt/log  && \
    mkdir -p /opt/nginx && \
    mkdir -p /opt/nginx/cache && \
    mkdir -p /opt/supervisor/ && \
    mkdir -p /run/sshd

ENV PYTHONPATH          /opt/

COPY /server/sshd_config /etc/ssh/

EXPOSE 5100 2222

ENTRYPOINT ["./entrypoint.sh"]

