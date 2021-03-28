FROM node:14-buster-slim AS builder
LABEL maintainer="Pouria Hadjibagheri <Pouria.Hadjibagheri@phe.gov.uk>"

WORKDIR /app/static

COPY ./app/static                     /app/static

RUN rm -rf node_modules
RUN npm install
RUN npm rebuild node-sass
RUN npm run build /app/static
RUN rm -rf node_modules


FROM python:3.9.2-buster
LABEL maintainer="Pouria Hadjibagheri <Pouria.Hadjibagheri@phe.gov.uk>"

# Gunicorn binding port
ENV GUNICORN_PORT 5200

COPY server/install-nginx.sh          /install-nginx.sh

RUN bash /install-nginx.sh
RUN rm /etc/nginx/conf.d/default.conf


# Install Supervisord
RUN apt-get update                             && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y supervisor              && \
    rm -rf /var/lib/apt/lists/*

COPY server/base.nginx                /etc/nginx/nginx.conf
COPY server/upload.nginx              /etc/nginx/conf.d/upload.conf
COPY server/engine.nginx              /etc/nginx/conf.d/engine.conf


RUN addgroup --system --gid 123 app                                  && \
    adduser  --system --disabled-login --ingroup app                    \
             --no-create-home --home /nonexistent                       \
             --gecos "app user" --shell /bin/false --uid 123 app

# Gunicorn config
COPY server/gunicorn_conf.py          /gunicorn_conf.py

# Gunicorn entrypoint - used by supervisord
COPY server/start-gunicorn.sh         /start-gunicorn.sh
RUN chmod +x /start-gunicorn.sh

# Main service entrypoint - launches supervisord
COPY server/entrypoint.sh             /entrypoint.sh
RUN chmod +x /entrypoint.sh


WORKDIR /app

COPY --from=builder /app/static/dist ./static
COPY app/static/images               ./static/images
COPY app/static/icon                 ./static/icon
COPY app/static/govuk-frontend       ./static/govuk-frontend
COPY ./app                           ./app
COPY ./requirements.txt              ./requirements.txt

RUN python3 -m pip install --no-cache-dir -U pip                      && \
    python3 -m pip install --no-cache-dir setuptools                  && \
    python3 -m pip install -U --no-cache-dir -r ./requirements.txt    && \
    rm ./requirements.txt

# Custom Supervisord config
COPY server/supervisord.conf          /opt/supervisor/supervisord.conf

RUN mkdir -p /run/supervisord/                                    && \
    mkdir -p /opt/supervisor/                                     && \
    mkdir -p /opt/log/                                            && \
    mkdir -p /opt/gunicorn/                                       && \
    mkdir -p /opt/ngnix/                                          && \
    mkdir -p /opt/nginx/cache/                                    && \
    chgrp -R app /var/cache/nginx/                                && \
    chmod -R g+rw /var/cache/nginx/                               && \
    chgrp -R app /app/                                            && \
    chmod -R g+r /app/                                            && \
    chgrp -R app /opt/                                            && \
    chmod -R g+wr /opt/

USER app

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
