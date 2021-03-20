#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
import logging
from typing import Dict, Iterable, Union
from urllib.parse import urlparse
from json import dumps

# 3rd party:
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware

from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.tracer import Tracer
from opencensus.trace.span import SpanKind
from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES
from opencensus.trace import config_integration
from opencensus.trace.propagation.trace_context_http_header_format import TraceContextPropagator
from opencensus.ext.azure.common.protocol import (
    Data,
    Envelope,
    RemoteDependency,
    Request,
)
from opencensus.ext.azure.common import utils

# Internal:

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'TraceHeaderMiddleware'
]


HTTP_URL = COMMON_ATTRIBUTES['HTTP_URL']
HTTP_STATUS_CODE = COMMON_ATTRIBUTES['HTTP_STATUS_CODE']
HTTP_HOST = COMMON_ATTRIBUTES['HTTP_HOST']
HTTP_METHOD = COMMON_ATTRIBUTES['HTTP_METHOD']
HTTP_PATH = COMMON_ATTRIBUTES['HTTP_PATH']


config_integration.trace_integrations(['logging'])
config_integration.trace_integrations(['requests'])


class Exporter(AzureExporter):
    def span_data_to_envelope(self, sd):
        envelope = Envelope(
            iKey=self.options.instrumentation_key,
            tags=dict(utils.azure_monitor_context),
            time=sd.start_time,
        )

        envelope.tags['ai.operation.id'] = sd.context.trace_id
        if sd.parent_span_id:
            envelope.tags['ai.operation.parentId'] = '{}'.format(sd.parent_span_id)
        if sd.span_kind == SpanKind.SERVER:
            envelope.name = 'Microsoft.ApplicationInsights.Request'
            data = Request(
                id='{}'.format(sd.span_id),
                duration=utils.timestamp_to_duration(
                    sd.start_time,
                    sd.end_time,
                ),
                responseCode=str(sd.status.code),
                success=False,  # Modify based off attributes or status
                properties={},
            )
            envelope.data = Data(baseData=data, baseType='RequestData')
            data.name = ''
            if 'http.method' in sd.attributes:
                data.name = sd.attributes['http.method']
            if 'http.route' in sd.attributes:
                data.name = f"{data.name} {sd.attributes['http.route']}"
                envelope.tags['ai.operation.name'] = data.name
                data.properties['request.name'] = data.name
            elif 'http.path' in sd.attributes:
                data.properties['request.name'] = f"{data.name} {sd.attributes['http.path']}"
            if 'http.url' in sd.attributes:
                data.url = sd.attributes['http.url']
                data.properties['request.url'] = sd.attributes['http.url']
            if 'http.status_code' in sd.attributes:
                status_code = sd.attributes['http.status_code']
                data.responseCode = str(status_code)
                data.success = 200 <= status_code < 400
            elif sd.status.code == 0:
                data.success = True
        else:
            envelope.name = 'Microsoft.ApplicationInsights.RemoteDependency'
            data = RemoteDependency(
                name=sd.name,  # TODO
                id='{}'.format(sd.span_id),
                resultCode=str(sd.status.code),
                duration=utils.timestamp_to_duration(
                    sd.start_time,
                    sd.end_time,
                ),
                success=False,  # Modify based off attributes or status
                properties={},
            )

            envelope.data = Data(baseData=data, baseType='RemoteDependencyData')

            if sd.span_kind == SpanKind.CLIENT:
                data.type = sd.attributes.get('component')
                if 'http.url' in sd.attributes:
                    url = sd.attributes['http.url']
                    # TODO: error handling, probably put scheme as well
                    data.data = url
                    parse_url = urlparse(url)
                    # target matches authority (host:port)
                    data.target = parse_url.netloc
                    if 'http.method' in sd.attributes:
                        # name is METHOD/path
                        data.name = f"{sd.attributes['http.method']}  {parse_url.path}"
                if 'http.status_code' in sd.attributes:
                    status_code = sd.attributes["http.status_code"]
                    data.resultCode = str(status_code)
                    data.success = 200 <= status_code < 400
                elif sd.status.code == 0:
                    data.success = True

            elif "dependency.type" in sd.attributes:
                data.type = sd.attributes.pop("dependency.type")
                for key, value in dict(sd.attributes).items():
                    if key == f"{data.type}.success":
                        data.success = value

                        sd.attributes[f"{data.type}.status_code"] = 200 if value else 500
                        continue

                    if key.startswith(data.type):
                        data.properties["error"] = f"{value}"
                # if f"{data.type}.query" in sd.attributes:
                #     data.data = sd.attributes.pop(f"{data.type}.query")
                # if f"{data.type}.error" in sd.attributes:
                #     data.success = False
                #     data.properties["error"] = sd.attributes.pop(f"{data.type}.error")

            else:
                data.type = 'INPROC'
                data.success = True
        if sd.links:
            links = []
            for link in sd.links:
                links.append({
                    "operation_Id": link.trace_id,
                    "id": link.span_id
                })
            data.properties["_MS.links"] = dumps(links)

        # TODO: tracestate, tags
        for key in sd.attributes:
            # This removes redundant data from ApplicationInsights
            if key.startswith('http.'):
                continue
            data.properties[key] = sd.attributes[key]
        return envelope


class TraceHeaderMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, sampler, instrumentation_key, cloud_role_name,
                 extra_attrs: Dict[str, str],
                 logging_instances: Iterable[Iterable[Union[logging.Logger, int]]]):

        self.exporter = Exporter(connection_string=instrumentation_key)
        self.exporter.add_telemetry_processor(cloud_role_name)

        self.app = app

        self.sampler = sampler
        self.extra_attrs = extra_attrs

        self.handler = AzureLogHandler(connection_string=instrumentation_key)

        self.handler.add_telemetry_processor(cloud_role_name)
        super(TraceHeaderMiddleware, self).__init__(app)

        for log, level in logging_instances:
            log.addHandler(self.handler)
            log.setLevel(level)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        propagator = TraceContextPropagator()
        span_context = propagator.from_headers(dict(scope['headers']))

        tracer = Tracer(
            exporter=self.exporter,
            sampler=self.sampler,
            span_context=span_context
        )
        tracer.span_context.trace_options.set_enabled(True)

        with tracer.span("main") as span:
            span.span_kind = SpanKind.SERVER
            if "traceparent" not in scope['headers']:
                trace_ctx = span.context_tracer
                trace_options = tracer.span_context.trace_options.trace_options_byte
                trace_id = trace_ctx.trace_id
                trace_parent = f"00-{trace_id}-{span.span_id}-{trace_options}"
                scope['headers'].append((b'traceparent', trace_parent.encode()))

        await self.app(scope, receive, send)

    async def dispatch(self, request: Request, call_next):
        propagator = TraceContextPropagator()
        span_context = propagator.from_headers(dict(request.headers))

        tracer = Tracer(
            exporter=self.exporter,
            sampler=self.sampler,
            span_context=span_context,
            propagator=propagator
        )

        with tracer.span("main") as span:
            span.span_kind = SpanKind.SERVER
            tracer.add_attribute_to_current_span(HTTP_URL, str(request.url))
            tracer.add_attribute_to_current_span(HTTP_HOST, request.url.hostname)
            tracer.add_attribute_to_current_span(HTTP_METHOD, request.method)
            tracer.add_attribute_to_current_span(HTTP_PATH, request.url.path)
            tracer.add_attribute_to_current_span("x_forwarded_host", request.headers.get("x_forwarded_host"))

            for key, value in self.extra_attrs:
                tracer.add_attribute_to_current_span(key, value)

            response = await call_next(request)

            tracer.add_attribute_to_current_span(HTTP_STATUS_CODE, str(response.status_code))

        return response
