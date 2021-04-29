#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import Union
from http import HTTPStatus
from asyncio import gather
from ssl import SSLContext, PROTOCOL_TLSv1_2, CERT_REQUIRED

# 3rd party:
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from aioredis import create_connection
import certifi

# Internal:
from app.database.postgres import Connection
from app.storage import AsyncStorageClient
from app.config import Settings

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'run_healthcheck'
]


ssl_context = SSLContext(PROTOCOL_TLSv1_2)
ssl_context.verify_mode = CERT_REQUIRED
ssl_context.check_hostname = True
ssl_context.load_default_certs()
ssl_context.load_verify_locations(certifi.where())


async def test_db():
    async with Connection() as conn:
        db_active = await conn.fetchval("SELECT 1 AS passed;")

    return {"db": f"healthy - {db_active}"}


async def test_storage():
    async with AsyncStorageClient("pipeline", "info/seen") as blob_client:
        blob = await blob_client.download()
        blob_data = await blob.readall()

    return {"storage": f"healthy - {blob_data.decode()}"}


# async def test_redis():
#     redis = await create_connection(
#         Settings.redis['address'],
#         password=Settings.redis["password"],
#         timeout=1,
#         ssl=SSLContext
#     )
#
#     response = await redis.execute("EXEC", "PING")
#
#     return {"storage": f"healthy - {response}"}


async def run_healthcheck(request: Request) -> Union[JSONResponse, Response]:
    response = await gather(test_db(), test_storage())

    if request.method == 'GET':
        return JSONResponse(response, status_code=HTTPStatus.OK.real)

    return Response(content=None, status_code=HTTPStatus.NO_CONTENT.real)
