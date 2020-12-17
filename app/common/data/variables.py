#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from typing import Dict, Callable, Union

# 3rd party:

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DestinationMetrics = {
    'cases': {
        "metric": 'newCasesByPublishDate',
        "caption": "Cases",
        "heading": "People tested positive",
        "postcode_destination": "ltla",
        "rate_offset": 5  # days
    },
    'deaths': {
        "metric": 'newDeaths28DaysByPublishDate',
        "caption": "Deaths",
        "heading": "Deaths within 28 days of positive test",
        "postcode_destination": "ltla",
        "rate_offset": 5  # days
    },
    'healthcare': {
        "metric": 'newAdmissions',
        "caption": "Healthcare",
        "heading": "Patients admitted",
        "postcode_destination": "nhsTrust",
        "rate_offset": 0  # days
    },
    'testing': {
        "metric": 'newVirusTests',
        "caption": "Testing",
        "heading": "Virus tests conducted",
        "postcode_destination": "nation"
    }
}


AreaTypeNames = {
    "nhsRegion": "Healthcare Region",
    "nhsTrust": "Healthcare Trust",
    "ltla": "Local Authority (Lower tier)",
    "utla": "Local Authority (Upper tier)",
    "region": "Region",
    "nation": "Nation"
}


AreaTypeShortNames = {
    "nhsRegion": "Healthcare",
    "nhsTrust": "Healthcare",
    "ltla": "Local Authority",
    "utla": "Local Authority",
    "region": "Region",
    "nation": "Nation"
}


NationalAdjectives = {
    "England": "English",
    "Wales": "Welsh",
    "Scotland": "Scottish",
    "Northern Ireland": "Northern Irish"
}


IsImproving: Dict[str, Callable[[Union[int, float]], bool]] = {
    "newCasesByPublishDate": lambda x: x < 0,
    "newDeaths28DaysByPublishDate": lambda x: x < 0,
    "newVirusTests": lambda x: 0,
    "newAdmissions": lambda x: x < 0,
}
