#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:

# 3rd party:
from asyncio import get_event_loop
from aioredis import create_redis_pool

import ssl
import certifi

# Internal:

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'instantiate_redis_pool'
]


ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
ssl_context.verify_mode = ssl.CERT_REQUIRED
ssl_context.check_hostname = True
ssl_context.load_default_certs()
ssl_context.load_verify_locations(certifi.where())


async def instantiate_redis_pool(address, password, maxsize):
    conn = await create_redis_pool(
        address=address,
        password=password,
        loop=get_event_loop(),
        minsize=5,
        maxsize=maxsize,
        ssl=ssl_context,
    )

    return conn


# class RedisContextMiddleware(BaseHTTPMiddleware):
#     def __init__(self, *args, address, password, maxsize, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.address = address
#         self.password = password
#         self.maxsize = maxsize
#
#     async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
#         if get_redis_pool() is None:
#             pool = await instantiate_redis_pool(self.address, self.password, self.maxsize)
#             set_redis_pool(pool)
#
#         response = await call_next(request)
#         try:
#             return response
#         finally:
#             await shutdown_redis_pool()
#
