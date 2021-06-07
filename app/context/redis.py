#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from typing import Any
from contextvars import ContextVar
from asyncio import get_event_loop
import ssl

# 3rd party:
from aioredis import create_redis_pool

import certifi

# Internal:
from app.config import Settings

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


REQUEST_ID_CTX_KEY = "redis_pool"

redis_pool_ctx_var: ContextVar[Any] = ContextVar(REQUEST_ID_CTX_KEY, default=None)


ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
ssl_context.verify_mode = ssl.CERT_REQUIRED
ssl_context.check_hostname = True
ssl_context.load_default_certs()
ssl_context.load_verify_locations(certifi.where())


async def instantiate_redis_pool():
    if (pool := get_redis_pool()) is not None:
        return pool

    conn = await create_redis_pool(
        **Settings.redis,
        minsize=10,
        loop=get_event_loop(),
        ssl=ssl_context if Settings.DEBUG else None,  # Prod goes via VNet
    )

    return conn


def get_redis_pool():
    return redis_pool_ctx_var.get()


def set_redis_pool(pool: Any):
    return redis_pool_ctx_var.set(pool)


async def shutdown_redis_pool():
    pool = get_redis_pool()
    set_redis_pool(None)
    try:
        pool.close()
        await pool.wait_closed()
    except AttributeError:
        pass
