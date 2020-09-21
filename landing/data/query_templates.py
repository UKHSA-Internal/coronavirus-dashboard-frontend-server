#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from string import Template

# 3rd party:

# Internal:

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'LastFortnight',
    'PostcodeLookup',
    'LookupByAreaCode',
    'DataByAreaCode'
]


LastFortnight = Template("""\
SELECT
    VALUE {
        'date':  c.date, 
        'value': c.$metric
    }
FROM     c
WHERE    c.releaseTimestamp = @releaseTimestamp
     AND c.areaNameLower    = @areaName
     AND IS_DEFINED(c.$metric)
ORDER BY c.releaseTimestamp DESC,
         c.date             DESC,
         c.areaType         ASC,
         c.areaNameLower    ASC\
""")


PostcodeLookup = """\
SELECT
    c.msoa,
    c.ltla
FROM     c
WHERE    c.type            = 'postcode'
     AND c.trimmedPostcode = @postcode\
"""


LookupByAreaCode = """\
SELECT 
    c.areaName,
    c.destinations
FROM c
WHERE   c.type     = 'general'
    AND c.areaCode = @areaCode
    AND (
      (c.areaType = 'ltla' AND c.parent.areaCode != @areaCode)
      OR c.areaType = 'utla'
    )\
"""


DataByAreaCode = Template("""\
SELECT  
    TOP 14 VALUE {
        'areaName': c.areaName,
        'areaType': c.areaType,
        'date': c.date,
        'value': c.$metric
    }
FROM    c 
WHERE   
        c.seriesDate       = @seriesDate
    AND c.releaseTimestamp = @releaseTimestamp
    AND c.areaType         = @areaType
    AND c.areaNameLower    = @areaName
    AND IS_DEFINED(c.$metric)
ORDER BY 
    c.date DESC\
""")
