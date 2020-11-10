#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:

# 3rd party:

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

DestinationMetrics = {
    'cases': {
        "metric": 'newCasesByPublishDate',
        "caption": "Cases",
        "heading": "People tested positive",
    },
    'deaths': {
        "metric": 'newDeaths28DaysByPublishDate',
        "caption": "Deaths",
        "heading": "Deaths within 28 days of positive test",
    },
    'healthcare': {
        "metric": 'newAdmissions',
        "caption": "Healthcare",
        "heading": "Patients admitted",
    },
    'testing': {
        "metric": 'newPCRTestsByPublishDate',
        "caption": "Testing",
        "heading": "Virus tests processed by laboratories",
    }
}

AreaTypeNames = {
    "nhsRegion": "Healthcare Region",
    "ltla": "Local Authority (Lower tier)",
    "utla": "Local Authority (Upper tier)",
    "region": "Region",
    "nation": "Nation"
}

AreaTypeShortNames = {
    "nhsRegion": "Healthcare",
    "ltla": "Local Authority",
    "utla": "Local Authority",
    "region": "Region",
    "nation": "Nation"
}
