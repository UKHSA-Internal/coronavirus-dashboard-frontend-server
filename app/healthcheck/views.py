#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:

# 3rd party:
from starlette.responses import JSONResponse, Response

# Internal:
from ..database.postgres import Connection

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'healthcheck'
]


async def healthcheck(request):
    async with Connection() as conn:
        result = await conn.fetchval("SELECT NOW() AS timestamp;")

    if request.method == "GET":
        return JSONResponse({"timestamp": result.isoformat()})

    return Response(status_code=204)
