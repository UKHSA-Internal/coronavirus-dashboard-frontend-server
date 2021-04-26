#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import Union
from http import HTTPStatus
from asyncio import gather

# 3rd party:
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Internal:
from app.database.postgres import Connection
from app.storage import AsyncStorageClient
from app.caching import Redis

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'run_healthcheck'
]


async def test_db():
    async with Connection() as conn:
        db_active = await conn.fetchval("SELECT 1 AS passed;")

    return {"db": f"healthy - {db_active}"}


async def test_storage():
    async with AsyncStorageClient("pipeline", "info/seen") as blob_client:
        blob = await blob_client.download()
        blob_data = await blob.readall()

    return {"storage": f"healthy - {blob_data.decode()}"}


async def test_redis():
    redis = Redis()
    response = await redis.ping()

    return {"storage": f"healthy - {response}"}


async def run_healthcheck(request: Request) -> Union[JSONResponse, Response]:
    response = await gather(test_db(), test_storage(), test_redis())

    if request.method == 'GET':
        return JSONResponse(response, status_code=HTTPStatus.OK.real)

    return Response(content=None, status_code=HTTPStatus.NO_CONTENT.real)
