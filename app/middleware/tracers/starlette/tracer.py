#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from typing import Dict

# 3rd party:
from starlette.requests import Request

from starlette.middleware.base import BaseHTTPMiddleware

from opencensus.trace.tracer import Tracer
from opencensus.trace.span import SpanKind
from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES
from opencensus.trace import config_integration
from opencensus.trace.propagation.trace_context_http_header_format import TraceContextPropagator

# Internal:

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'TraceRequestMiddleware'
]


HTTP_URL = COMMON_ATTRIBUTES['HTTP_URL']
HTTP_STATUS_CODE = COMMON_ATTRIBUTES['HTTP_STATUS_CODE']
HTTP_HOST = COMMON_ATTRIBUTES['HTTP_HOST']
HTTP_METHOD = COMMON_ATTRIBUTES['HTTP_METHOD']
HTTP_PATH = COMMON_ATTRIBUTES['HTTP_PATH']
HTTP_ROUTE = COMMON_ATTRIBUTES['HTTP_ROUTE']


config_integration.trace_integrations(['logging'])
config_integration.trace_integrations(['requests'])


logger = logging.getLogger("app")


class TraceRequestMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, sampler, extra_attrs: Dict[str, str]):

        self.app = app

        self.sampler = sampler
        self.extra_attrs = extra_attrs

        super(TraceRequestMiddleware, self).__init__(app)

    async def dispatch(self, request: Request, call_next):
        propagator = TraceContextPropagator()
        span_context = propagator.from_headers(dict(request.headers))

        tracer = Tracer(
            exporter=request.app.state.azure_exporter,
            sampler=self.sampler,
            span_context=span_context,
            propagator=propagator
        )

        try:
            # tracer.span_context.trace_options.set_enabled(True)
            span = tracer.start_span()
            span.name = f"[{request.method}] {request.url.path}"
            span.span_kind = SpanKind.SERVER
            # if "traceparent" not in request.headers:
            #     trace_ctx = span.context_tracer
            #     trace_options = tracer.span_context.trace_options.trace_options_byte
            #     trace_id = trace_ctx.trace_id
            #     trace_parent = f"00-{trace_id}-{span.span_id}-0{trace_options}"
            # else:
            #     trace_parent = request.headers['traceparent']

            span.add_attribute(HTTP_URL, str(request.url))
            span.add_attribute(HTTP_HOST, request.url.hostname)
            span.add_attribute(HTTP_METHOD, request.method)
            span.add_attribute(HTTP_PATH, request.url.path)
            if not len(request.query_params):
                span.add_attribute(HTTP_ROUTE, request.url.path)
            else:
                span.add_attribute(HTTP_ROUTE, f"{request.url.path}?{request.url.query}")

            span.add_attribute("x_forwarded_host", request.headers.get("x_forwarded_host"))

            for key, value in self.extra_attrs.items():
                span.add_attribute(key, value)

            try:
                response = await call_next(request)
                span.add_attribute(HTTP_STATUS_CODE, response.status_code)
                return response
            except Exception as err:
                span.add_attribute(HTTP_STATUS_CODE, "500")
                raise err
            finally:
                tracer.end_span()

        except Exception as err:
            logger.error(err, exc_info=True)
            raise err
        finally:
            tracer.finish()
