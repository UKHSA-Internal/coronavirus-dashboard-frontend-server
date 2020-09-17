#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import Union, List, Dict, Iterable

# 3rd party:

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ItemType = Dict[
    str,
    Union[str, float, int, bool, list, dict]
]

ParametersType = List[ItemType]

ResponseType = Union[List, Dict]

PaginatedResponse = Union[
    Iterable[ResponseType],
    Iterable[Iterable[ResponseType]]
]
