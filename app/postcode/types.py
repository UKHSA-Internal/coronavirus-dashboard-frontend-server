#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import TypedDict, List, Dict, Union

# 3rd party:

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    "LocalDataType",
    "QueryDataType"
]


class LocalDataType(TypedDict):
    column_names: List[str]
    msoa_metric: str
    getter_metrics: List[str]
    metrics: List[str]


class QueryDataType(TypedDict):
    local_data: LocalDataType

