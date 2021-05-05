#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from inspect import signature
from hashlib import blake2b
from random import randint
from functools import wraps
from pickle import loads, dumps
from asyncio import Future, get_event_loop

# 3rd party:
from pandas import DataFrame

# Internal: 
from app.middleware.tracers.utils import trace_async_method_operation
from app.config import Settings

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'Redis',
    'from_cache_or_func',
    'from_cache_or_db'
]


class Redis:
    _name = "Redis"

    def __init__(self, request, raw_key=None):
        self._connection = request.app.state.redis

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

    async def __aenter__(self):
        self._conn = (await self._connection).__enter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._conn.__exit__()

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
        return await self._conn.set(key, value, expire=expire)

    @trace_async_method_operation(
        "url",
        name="account_name",
        dep_type="_name",
        action="MGET"
    )
    async def mget(self, *keys):
        return await self._conn.mget(*keys)

    @trace_async_method_operation(
        "url",
        name="account_name",
        dep_type="_name",
        action="GET"
    )
    async def ping(self):
        return await self._conn.ping()


async def from_cache_or_func(request, func, prefix, expire, with_request=False, *args, **kwargs):
    key = [*args, *kwargs.values()]
    raw_key = str.join("|", map(str, key))
    cache_key = prefix + blake2b(raw_key.encode(), digest_size=6).hexdigest()

    async with Redis(request, raw_key) as redis:
        redis_result = await redis.get(cache_key)

        if redis_result is not None:
            return loads(redis_result)

        if with_request:
            result = await func(request, *args, **kwargs)
        else:
            result = await func(*args, **kwargs)

        await redis.set(cache_key, dumps(result), expire)

    return result


async def from_cache(request, future: Future, key, raw_key):
    async with Redis(request, raw_key) as redis:
        if (result := await redis.get(key)) is not None and not future.done():
            result = loads(result)
            future.set_result(result)
            future.done()


async def from_db(request, future: Future, func, key, raw_key, *args, **kwargs):
    result: DataFrame = await func(request, *args, **kwargs, loop=future.get_loop())

    if not future.done():
        async with Redis(request, raw_key) as redis:
            await redis.set(
                key=key,
                value=dumps(result),
                expire=randint(5 * 60, 8 * 60) * 60  # Between 5 and 8 hours
            )

    if not future.done():
        future.set_result(result)
        future.done()


def from_cache_or_db(prefix):
    def outer(func):
        sig = signature(func)

        @wraps(func)
        async def inner(*args, **kwargs):
            bound_inputs = sig.bind(*args, **kwargs)
            request = bound_inputs.arguments.pop("request")
            key = [*bound_inputs.args, *bound_inputs.kwargs.values()]
            raw_key = str.join("|", map(str, key))

            cache_key = prefix + blake2b(raw_key.encode(), digest_size=6).hexdigest()

            loop = get_event_loop()
            future = loop.create_future()

            loop.create_task(
                from_cache(request, future, cache_key, prefix + raw_key)
            )

            loop.create_task(
                from_db(
                    request, future, func, cache_key, prefix + raw_key,
                    *bound_inputs.args, **bound_inputs.kwargs
                )
            )

            await future
            return future.result()

        return inner
    return outer
