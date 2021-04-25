#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import Any
from contextvars import ContextVar

# 3rd party:

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


REQUEST_ID_CTX_KEY = "redis_pool"

redis_pool_ctx_var: ContextVar[Any] = ContextVar(REQUEST_ID_CTX_KEY, default=None)


def get_redis_pool():
    return redis_pool_ctx_var.get()


def set_redis_pool(pool: Any):
    return redis_pool_ctx_var.set(pool)


async def shutdown_redis_pool():
    pool = get_redis_pool()
    set_redis_pool(None)
    pool.close()
    await pool.wait_closed()
