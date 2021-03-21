#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import Any
from logging import getLogger
from os import getenv

# 3rd party:
from asyncpg import connect, Connection as PGConnection
from orjson import loads, dumps

from asyncpg.exceptions import PostgresLogMessage

# Internal:
from app.middleware.tracers.utils import trace_async_method_operation

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    "Connection"
]


CONN_STR = getenv("POSTGRES_CONNECTION_STRING")
DB_NAME = "database"

logger = getLogger("asyncpg")


class Connection:
    conn: Any
    _name = "postgresql"

    def __init__(self, conn_str=CONN_STR):
        self.conn_str = conn_str
        self._connection = connect(self.conn_str)
        self._account_name = DB_NAME

    def __await__(self):
        yield from self._connection.__await__()

    async def __aenter__(self) -> PGConnection:
        self._conn = await self._connection
        await self._conn.set_type_codec(
            'jsonb',
            encoder=dumps,
            decoder=loads,
            schema='pg_catalog'
        )
        # self._conn.add_log_listener(logger)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self._conn.close()

    @trace_async_method_operation(
        name="_account_name",
        dep_type="_name",
        action="fetchval"
    )
    async def fetchval(self, query, *args, **kwargs):
        return await self._conn.fetchval(query, *args, **kwargs)

    @trace_async_method_operation(
        name="_account_name",
        dep_type="_name",
        action="fetch"
    )
    async def fetch(self, query, *args, **kwargs):
        return await self._conn.fetch(query, *args, **kwargs)

    @trace_async_method_operation(
        name="_account_name",
        dep_type="_name",
        action="fetchrow"
    )
    async def fetchrow(self, query, *args, **kwargs):
        return await self._conn.fetchrow(query, *args, **kwargs)
