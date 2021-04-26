#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from logging import getLogger
from functools import wraps
from inspect import signature
from datetime import datetime

# 3rd party:
from opencensus.trace.execution_context import get_opencensus_tracer
from opencensus.trace.span import SpanKind

# Internal:

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'trace_async_method_operation',
    'trace_method_operation'
]


logger = getLogger(__name__)


def format_query(query, *args):
    for index, sub in enumerate(args, start=1):
        if isinstance(sub, (int, float)):
            query = query.replace(f"${index}", f"{sub}")
        elif isinstance(sub, str):
            query = query.replace(f"${index}", f"'{sub}'")
        elif isinstance(sub, datetime):
            query = query.replace(f"${index}", f"'{sub.isoformat()}'")
        elif not isinstance(sub, list):
            query = query.replace(f"${index}", f"'{sub}'")
        else:
            query = query.replace(f"${index}", f"'{{{str.join(',', sub)}}}'")

    return query


def trace_async_method_operation(*cls_attrs, dep_type="name", name="name", **attrs):
    def wrapper(func):
        sig = signature(func)

        @wraps(func)
        async def process(klass, *args, **kwargs):
            nonlocal sig, name, cls_attrs, attrs
            cls_attrs = list(cls_attrs)

            bound_inputs = sig.bind(klass, *args, **kwargs)

            tracer = get_opencensus_tracer()

            if tracer is None:
                return await func(*bound_inputs.args, **bound_inputs.kwargs)

            span = tracer.start_span()
            span.span_kind = SpanKind.UNSPECIFIED
            span.name = getattr(klass, name, None)

            if "operation" in attrs:
                span.name = f'{attrs.pop("operation")} {span.name}'

            dependency_type = getattr(klass, dep_type)
            span.add_attribute('dependency.type', dependency_type)

            if "url" in cls_attrs and dependency_type.lower() == "azure blob":
                cls_attrs.remove("url")
                span.add_attribute(f"{dependency_type}.data", getattr(klass, "url", None))

            if "query" in bound_inputs.arguments:
                args = list()
                if "args" in bound_inputs.arguments:
                    args = bound_inputs.arguments["args"]

                query = format_query(bound_inputs.arguments['query'], *args)
                span.add_attribute(f"{dependency_type}.query", query)
                span.add_attribute(f"{dependency_type}.method.name", func.__name__)
            elif "expire" in bound_inputs.arguments:
                span.add_attribute(f"{dependency_type}.expire", f"{bound_inputs.arguments['expire']} s")

            for key in cls_attrs:
                span.add_attribute(f"{dependency_type}.{key}", getattr(klass, key, None))

            for key, value in attrs.items():
                span.add_attribute(f"{dependency_type}.{key}", value)

            success = True
            try:
                result = await func(klass, *args, **kwargs)

                if dependency_type.lower() == "redis" and (
                        attrs.get("action", None) == "get" or
                        func.__name__ == "get"):
                    span.add_attribute(f"{dependency_type}.cache", "HIT" if result is not None else "MISS")

                return result
            except Exception as err:
                success = False
                logger.exception(err, exc_info=True)
                span.add_attribute(f'{dependency_type}.error', err)
                raise err
            finally:
                span.add_attribute(f'{dependency_type}.success', success)
                tracer.end_span()

        return process

    return wrapper


def trace_method_operation(*cls_attrs, dep_type="name", name="name", **attrs):
    def wrapper(func):
        sig = signature(func)

        @wraps(func)
        def process(klass, *args, **kwargs):
            nonlocal sig, name, cls_attrs, attrs
            cls_attrs = list(cls_attrs)

            bound_inputs = sig.bind(klass, *args, **kwargs)

            tracer = get_opencensus_tracer()

            if tracer is None:
                return func(*bound_inputs.args, **bound_inputs.kwargs)

            span = tracer.start_span()
            span.span_kind = SpanKind.UNSPECIFIED
            span.name = getattr(klass, name, None)

            if "operation" in attrs:
                span.name = f'{attrs.pop("operation")} {span.name}'

            dependency_type = getattr(klass, dep_type)
            span.add_attribute('dependency.type', dependency_type)

            if "url" in cls_attrs and dependency_type.lower() == "azure blob":
                cls_attrs.remove("url")
                span.add_attribute(f"{dependency_type}.data", getattr(klass, "url", None))

            if "query" in bound_inputs.arguments:
                span.add_attribute(f"{dependency_type}.query", bound_inputs.arguments['query'])
                span.add_attribute(f"{dependency_type}.method.name", func.__name__)

            for key in cls_attrs:
                span.add_attribute(f"{dependency_type}.{key}", getattr(klass, key, None))

            for key, value in attrs.items():
                span.add_attribute(f"{dependency_type}.{key}", value)

            success = True
            try:
                return func(klass, *args, **kwargs)
            except Exception as err:
                success = False
                logger.exception(err, exc_info=True)
                raise err
            finally:
                span.add_attribute(f'{dependency_type}.success', success)
                tracer.end_span()

        return process

    return wrapper
