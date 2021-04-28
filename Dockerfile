FROM node:14-buster-slim AS builder
LABEL maintainer="Pouria Hadjibagheri <Pouria.Hadjibagheri@phe.gov.uk>"

WORKDIR /app/static

COPY ./app/static                     /app/static

RUN rm -rf node_modules
RUN npm install
RUN npm rebuild node-sass
RUN npm run build /app/static
RUN rm -rf node_modules

FROM nginx/unit:1.23.0-python3.9

WORKDIR /opt

COPY requirements.txt       ./config/requirements.txt

RUN apt update                                                   && \
    pip3 install -r /opt/config/requirements.txt                 && \
    apt remove -y python3-pip                                    && \
    apt autoremove --purge -y                                    && \
    rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.d/*.list   && \
    rm -rf /opt/config/requirements.txt


COPY --from=builder /app/static/dist /opt/static
COPY app/static/images               /opt/static/images
COPY app/static/icon                 /opt/static/icon
COPY app/static/govuk-frontend       /opt/static/govuk-frontend
COPY ./app                           /opt/app


COPY server/*.json      /docker-entrypoint.d/

RUN chown -R unit:unit  /opt

RUN touch /opt/.netrc             && \
    chown unit:unit  /opt/.netrc

ENV NETRC    /opt/.netrc
ENV PYTHONPATH          /opt/app

EXPOSE 5100
