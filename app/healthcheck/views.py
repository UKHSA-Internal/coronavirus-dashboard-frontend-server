#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import Union
from http import HTTPStatus
from asyncio import gather, get_running_loop, Lock

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
        db_active = await conn.fetchval("SELECT TRUE AS passed;")

    return {"db": db_active is True}


async def test_storage():
    async with AsyncStorageClient("pipeline", "info/seen") as blob_client:
        data = await blob_client.exists()

    return {"storage": data is True}


async def test_redis(request):
    async with Redis(request) as redis:
        response = await redis.ping()

    return {"redis": response == b"PONG"}


async def run_healthcheck(request: Request) -> Union[JSONResponse, Response]:
    response = await gather(test_db(), test_storage(), test_redis(request))

    if request.method == 'GET':
        return JSONResponse(response, status_code=HTTPStatus.OK.real)

    return Response(content=None, status_code=HTTPStatus.NO_CONTENT.real)
