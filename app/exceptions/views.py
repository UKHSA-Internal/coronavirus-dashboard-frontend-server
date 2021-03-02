#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from http import HTTPStatus
from functools import wraps

# 3rd party:

# Internal:
from ..template_processor import render_template

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'exception_handlers'
]


async def handle_404(request, exc, **context):
    # if isinstance(err, HandledException):
    #     return err

    # app.logger.info(f"404 - Not found", extra={'custom_dimensions': {"url": request.url}})

    status = HTTPStatus.NOT_FOUND
    status_code = getattr(status, "value", 404)
    status_detail = getattr(status, "phrase", "Not Found")

    return await render_template(
        request,
        "errors/404.html",
        context={
            "status_code": status_code,
            "status_detail": status_detail,
            **context
        },
        status_code=status_code
    )


async def handle_500(request, exc, **context):
    # if isinstance(err, HandledException):
    #     return err

    # additional_info = {
    #     'website_timestamp': g.website_timestamp,
    #     'latest_release': g.timestamp,
    #     'db_host': getenv("AzureCosmosHost", NOT_AVAILABLE),
    #     "API_environment": getenv("API_ENV", NOT_AVAILABLE),
    #     "server_location": getenv("SERVER_LOCATION", NOT_AVAILABLE),
    #     "is_dev": getenv("IS_DEV", NOT_AVAILABLE),
    #     "redis": getenv("AZURE_REDIS_HOST", NOT_AVAILABLE),
    #     "AzureCosmosDBName": getenv("AzureCosmosDBName", NOT_AVAILABLE),
    #     "AzureCosmosCollection": getenv("AzureCosmosCollection", NOT_AVAILABLE),
    #     "AzureCosmosDestinationsCollection": getenv(
    #         "AzureCosmosDestinationsCollection",
    #         NOT_AVAILABLE
    #     ),
    # }
    #
    # app.logger.exception(err, extra={'custom_dimensions': additional_info})

    if hasattr(exc, "status_code"):
        status_code = getattr(exc, "status_code")
        status_detail = getattr(exc, "phrase", "detail")
    else:
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        status_code = getattr(status, "value", 500)
        status_detail = getattr(status, "phrase", "Internal Server Error")

    return await render_template(
        request,
        "errors/50x.html",
        context={
            "status_code": status_code,
            "status_detail": status_detail,
            **context
        },
        status_code=status_code
    )


exception_handlers = {
    404: handle_404,
    500: handle_500,
    502: handle_500,
    503: handle_500
}
