#!/bin/bash

app="covid19-dash-frontend"

docker build -t ${app} .

docker run -d -p 5000:5000 \
    --name=${app} \
    --env-file=$PWD/.env.dev \
    -v $PWD:/app ${app} \
