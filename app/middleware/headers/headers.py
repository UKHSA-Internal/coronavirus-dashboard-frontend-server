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
                # x_forwarded_host = headers[b"x-forwarded-host"].decode("ascii")
                headers[b"host"] = headers[b"x-forwarded-host"]
                scope["headers"] = tuple(headers.items())
                # scope["host"] = ()
                # (host, sep, port) = x_forwarded_host.partition(":")
                # if port is None:
                #     # scope["server"] = (host, 0)
                #     scope["host"] = host
                # else:
                #     # scope["server"] = (host, int(port))
                #     scope["host"] = f"{host}:{port}"

        return await self.app(scope, receive, send)
