#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from ssl import SSLContext, CERT_REQUIRED, PROTOCOL_TLSv1_2

# 3rd party:
import certifi
from aioredis import create_redis_pool
from aredis import StrictRedis

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
        # self._connection = create_redis_pool(
        #     **Settings.redis,
        #     minsize=5,
        #     ssl=ssl_context,
        #     timeout=10
        # )
        self._conn = StrictRedis(
            host=Settings.redis["address"][0],
            port=Settings.redis["address"][1],
            password=Settings.redis["password"],
            ssl=True,
            ssl_context=ssl_context,
            db=0,
            connect_timeout=2,
            retry_on_timeout=True
        )

        address = Settings.redis['address']
        if isinstance(address, (tuple, list)):
            self.account_name = address[0].split(".")[0]
            self.url = str.join(":", address)
        else:
            self.account_name = address.split(".")[0]
            self.url = address

        self._key = raw_key

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = key

    # def __await__(self):
    #     yield from self._connection.__await__()

    async def __aenter__(self):
        # self._conn = await self._conn
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        # self._conn.
        # self._conn.close()
        # await self._conn.wait_closed()

    @trace_async_method_operation(
        "url", "_key",
        name="account_name",
        dep_type="_name",
        action="GET"
    )
    async def get(self, key):
        return await self._conn.get(key)

    @trace_async_method_operation(
        "url", "_key",
        name="account_name",
        dep_type="_name",
        action="SET"
    )
    async def set(self, key, value, expire=None):
        return await self._conn.set(key, value, ex=expire)

    @trace_async_method_operation(
        "url",
        name="account_name",
        dep_type="_name",
        action="GET"
    )
    async def ping(self):
        return await self._conn.ping()
