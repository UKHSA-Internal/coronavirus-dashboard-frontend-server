#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import NoReturn
from inspect import signature
from hashlib import blake2b
from functools import wraps
from pickle import loads, dumps
from datetime import datetime
import logging

# 3rd party:
from pandas import DataFrame, read_json
from orjson import dumps as json_dumps, loads as json_loads

# Internal: 
from app.middleware.tracers.utils import trace_async_method_operation
from app.config import Settings

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'Redis',
    'from_cache_or_func',
    'from_cache_or_db',
    'FromCacheOrDBMainData',
    'FromCacheOrDB'
]


DEFAULT_CACHE_TTL = 36 * 60 * 60  # 36 hours in seconds
LONG_TERM_CACHE_TTL = 36 * 60 * 60 * 24 * 180  # 180 days


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


def from_cache_or_db(prefix, ttl=DEFAULT_CACHE_TTL):
    def outer(func):
        sig = signature(func)

        @wraps(func)
        async def inner(*args, **kwargs):
            bound_inputs = sig.bind(*args, **kwargs)
            request = bound_inputs.arguments.pop("request")
            try:
                area_id = bound_inputs.arguments["area_id"]
                if bound_inputs.arguments["area_type"] == "overview":
                    area_id = "UK"
                timestamp = datetime.strptime(bound_inputs.arguments["timestamp"], "%Y_%m_%d")
                raw_key = cache_key = f"area-{timestamp:%Y-%m-%d}-{area_id}"
            except KeyError:
                key = [*bound_inputs.args, *bound_inputs.kwargs.values()]
                raw_key = str.join("|", map(str, key))
                cache_key = prefix + blake2b(raw_key.encode(), digest_size=6).hexdigest()

            async with Redis(request, raw_key) as redis:
                redis_result = await redis.get(cache_key)

                if redis_result is not None:
                    result = (
                        read_json(redis_result, orient="records")
                        .rename(columns={
                            "area_type": "areaType",
                            "area_name": "areaName",
                            "area_code": "areaCode"
                        })
                    )
                    return result

                result: DataFrame = await func(request, *bound_inputs.args, **bound_inputs.kwargs)
                await redis.set(
                    key=cache_key,
                    value=(
                        result
                        .rename(columns={
                            "areaType": "area_type",
                            "areaName": "area_name",
                            "areaCode": "area_code"
                        })
                        .to_json(orient="records")
                    ),
                    expire=ttl
                )

            return result

        return inner
    return outer


class FromCacheOrDBBase:
    def __init__(self, prefix, ttl=DEFAULT_CACHE_TTL):
        self.prefix = prefix
        self.ttl = ttl

    def __call__(self, func):
        self.func = func
        self.sig = signature(func)

        return self._execute

    def cache_key(self, bound_inputs) -> str:
        raise NotImplementedError()

    async def _execute(self, *args, **kwargs):
        bound_inputs = self.sig.bind(*args, **kwargs)
        request = bound_inputs.arguments.pop("request")
        cache_key = self.cache_key(bound_inputs)

        async with Redis(request, cache_key) as redis:
            results = await redis.get(cache_key)

            if results is not None:
                return self.process_cache_results(results)

            results = await self.func(request, *bound_inputs.args, **bound_inputs.kwargs)
            db_results = self.process_db_results(results)
            await self._cache_results(redis, cache_key, db_results)

        return results

    def process_db_results(self, results: DataFrame) -> bytes:
        raise NotImplementedError()

    def process_cache_results(self, results: str) -> DataFrame:
        raise NotImplementedError()

    async def _cache_results(self, redis, cache_key: str, results: bytes) -> NoReturn:
        await redis.set(
            key=cache_key,
            value=results,
            expire=self.ttl
        )


class FromCacheOrDB(FromCacheOrDBBase):
    def __init__(self, prefix, ttl=None):
        super().__init__(prefix, ttl=ttl or LONG_TERM_CACHE_TTL)

    def cache_key(self, bound_inputs) -> str:
        key = [*bound_inputs.args, *bound_inputs.kwargs.values()]
        raw_key = f'{self.prefix}::{str.join("|", map(str, key))}'
        return raw_key

    def process_db_results(self, results) -> bytes:
        return json_dumps(list(map(dict, results)))

    def process_cache_results(self, results: str) -> DataFrame:
        return json_loads(results)


class FromCacheOrDBMainData(FromCacheOrDBBase):
    def cache_key(self, bound_inputs) -> str:
        try:
            area_id = bound_inputs.arguments["area_id"]
            if bound_inputs.arguments["area_type"] == "overview":
                area_id = "UK"
            timestamp = datetime.strptime(bound_inputs.arguments["timestamp"], "%Y_%m_%d")
            raw_key = f"{self.prefix}-{timestamp:%Y-%m-%d}-{area_id}"
        except KeyError:
            key = [*bound_inputs.args, *bound_inputs.kwargs.values()]
            raw_key = f'SUMMARY::{str.join("|", map(str, key))}'

        return raw_key

    def process_db_results(self, results: DataFrame) -> bytes:
        res = (
            results
            .rename(columns={
                "areaType": "area_type",
                "areaName": "area_name",
                "areaCode": "area_code"
            })
            .to_json(orient="records")
            .encode()
        )

        return res

    def process_cache_results(self, results: str) -> DataFrame:
        res = (
            read_json(results, orient="records")
            .rename(columns={
                "area_type": "areaType",
                "area_name": "areaName",
                "area_code": "areaCode"
            })
        )

        return res


