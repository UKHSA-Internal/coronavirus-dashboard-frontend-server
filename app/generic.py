#!/usr/bin python3

"""
<Description of the programme>

Author:        Pouria Hadjibagheri <pouria.hadjibagheri@phe.gov.uk>
Created:       30 Apr 2021
License:       MIT
Contributors:  Pouria Hadjibagheri
"""

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from pathlib import Path
# 3rd party:
from starlette.responses import FileResponse, Response

# Internal: 
from app.storage import AsyncStorageClient

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Header
__author__ = "Pouria Hadjibagheri"
__copyright__ = "Copyright (c) 2021, Public Health England"
__license__ = "MIT"
__version__ = "0.0.1"
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'favicon_png',
    'favicon_ico',
    'sitemap'
]


assets_path = Path(__file__).parent.joinpath("assets")


async def favicon_ico(request):
    return FileResponse(
        "assets/icon/favicon.ico",
        headers={"cache-control": "s-maxage=604800, max-age=86400, stale-while-revalidate=300"}
    )


async def favicon_png(request):
    return FileResponse(
        'assets/icon/favicon.png',
        headers={"cache-control": "s-maxage=604800, max-age=86400, stale-while-revalidate=300"}
    )


async def sitemap(request):
    async with AsyncStorageClient(
            container="publicdata",
            path="assets/supplements/sitemap.xml") as client:
        data_io = await client.download()
        raw_data = await data_io.readall()

    return Response(
        raw_data,
        media_type="application/xml",
        headers={"cache-control": "s-maxage=300, max-age=60, must-revalidate"}
    )
