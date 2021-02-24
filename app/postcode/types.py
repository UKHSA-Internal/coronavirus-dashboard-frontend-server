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
    "AlertsType",
    "AlertLevel",
    "QueryDataType",
    "DataItem"
]


class LocalDataType(TypedDict):
    column_names: List[str]
    msoa_metric: str
    getter_metrics: List[str]
    metrics: List[str]


class AlertLevel(TypedDict):
    value: str
    url: str
    level: int


AlertsType = Dict[str, Union[Dict[str, AlertLevel], dict]]


class QueryDataType(TypedDict):
    local_data: LocalDataType


class DataItem(TypedDict):
    date: str
    areaName: str
    areaType: str
    areaCode: str
    adjective: Union[str, None]
    raw: Union[str, float, None]
    value: Union[str, None]
