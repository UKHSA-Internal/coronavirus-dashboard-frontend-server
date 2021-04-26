#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:

# 3rd party:

# Internal: 
from app.context.redis import get_redis_pool
from app.middleware.tracers.utils import trace_async_method_operation

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = ['Redis']


class Redis:
    _name = "Redis"

    def __init__(self, raw_key=None):
        self._conn = get_redis_pool()
        if isinstance(self._conn.address, (tuple, list)):
            self.account_name = self._conn.address[0].split(".")[0]
            self.url = str.join(":", self._conn.address)
        else:
            self.account_name = self._conn.address.split(".")[0]
            self.url = self._conn.address

        self.key = raw_key

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
