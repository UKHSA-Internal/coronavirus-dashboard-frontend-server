#!/usr/bin python3


# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:

# 3rd party:

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'ProxyHeadersHostMiddleware'
]


class ProxyHeadersHostMiddleware:
    def __init__(self, app, *args, **kwargs):
        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] in ("http", "websocket"):
            headers = dict(scope["headers"])

            if b"x-forwarded-host" in headers:
                headers[b"host"] = headers[b"x-forwarded-host"]
                headers[b"x-forwarded-proto"] = b"https"
                headers[b"scheme"] = b"https"
                scope["scheme"] = "https"
                scope["headers"] = tuple(headers.items())

            # print(headers)
        return await self.app(scope, receive, send)
