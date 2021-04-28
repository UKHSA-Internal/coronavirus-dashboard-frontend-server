#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from ssl import SSLContext, CERT_REQUIRED, PROTOCOL_TLSv1_2

# 3rd party:
import certifi
from aioredis import create_redis_pool

# Internal: 
from app.middleware.tracers.utils import trace_async_method_operation
from app.config import Settings

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = ['Redis']


ssl_context = SSLContext(PROTOCOL_TLSv1_2)
ssl_context.verify_mode = CERT_REQUIRED
ssl_context.check_hostname = True
ssl_context.load_default_certs()
ssl_context.load_verify_locations(certifi.where())


class Redis:
    _name = "Redis"

    def __init__(self, raw_key=None):
        self._connection = create_redis_pool(
            **Settings.redis,
            minsize=5,
            ssl=ssl_context,
            timeout=10
        )

        address = Settings.redis['address']
        if isinstance(address, (tuple, list)):
            self.account_name = address[0].split(".")[0]
            self.url = str.join(":", address)
        else:
            self.account_name = address.split(".")[0]
            self.url = address

        self.key = raw_key

    def __await__(self):
        yield from self._connection.__await__()

    async def __aenter__(self):
        self._conn = await self._connection
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._conn.close()
        await self._conn.wait_closed()

    @trace_async_method_operation(
        "url", "key",
        name="account_name",
        dep_type="_name",
        action="GET"
    )
    async def get(self, key):
        return await self._conn.get(key)

    @trace_async_method_operation(
        "url", "key",
        name="account_name",
        dep_type="_name",
        action="SET"
    )
    async def set(self, key, value, expire=None):
        return await self._conn.set(key, value, expire=expire)

    @trace_async_method_operation(
        "url",
        name="account_name",
        dep_type="_name",
        action="GET"
    )
    async def ping(self):
        return await self._conn.ping()
