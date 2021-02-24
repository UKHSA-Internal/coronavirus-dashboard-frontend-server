#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from os import getenv

# 3rd party:
import asyncpg

# Internal:

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'Connection'
]


CONN_STR = getenv("POSTGRES_CONNECTION_STRING")


class Connection:
    def __init__(self, conn_str=CONN_STR):
        self.conn_str = conn_str
        self._connection = asyncpg.connect(self.conn_str)

    def __await__(self):
        yield from self._connection.__await__()

    def __aenter__(self):
        return self._connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self._connection.close()
