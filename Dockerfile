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

COPY server/base.nginx               ./nginx.conf
COPY server/upload.nginx              /etc/nginx/conf.d/upload.conf
COPY server/engine.nginx              /etc/nginx/conf.d/engine.conf


RUN addgroup --system --gid 102 app                                  && \
    adduser  --system --disabled-login --ingroup app                    \
             --no-create-home --home /nonexistent                       \
             --gecos "app user" --shell /bin/false --uid 102 app

# Gunicorn config
COPY server/gunicorn_conf.py          /gunicorn_conf.py

# Gunicorn entrypoint - used by supervisord
COPY server/start-gunicorn.sh         /start-gunicorn.sh
RUN chmod +x /start-gunicorn.sh

# Custom Supervisord config
COPY server/supervisord.conf          /etc/supervisor/conf.d/supervisord.conf

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

USER app

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
