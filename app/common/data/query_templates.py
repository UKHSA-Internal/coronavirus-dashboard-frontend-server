#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from string import Template

# 3rd party:

# Internal:

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'DataSinceApril',
    'PostcodeLookup',
    'LookupByAreaCode',
    'DataByAreaCode',
    'MsoaData',
    'AlertLevel',
    'SpecimenDateData',
    'LatestTransmissionRate',
    "HealthCheck",
    "Vaccinations"
]


DataSinceApril = Template("""\
SELECT
    VALUE {
        'date':  c.date, 
        'value': c.$metric
    }
FROM     c
WHERE    c.releaseTimestamp = @releaseTimestamp
     AND c.areaNameLower    = @areaName
     AND IS_DEFINED(c.$metric)
     AND c.date >= '2020-04-01'
ORDER BY c.releaseTimestamp DESC,
         c.date             DESC,
         c.areaType         ASC,
         c.areaNameLower    ASC\
""")


LatestData = Template("""\
SELECT TOP 1
    VALUE {
        'date':  c.date, 
        'value': c.$metric
    }
FROM     c
WHERE    c.releaseTimestamp = @releaseTimestamp
     AND c.areaNameLower    = @areaName
     AND IS_DEFINED(c.$metric)
ORDER BY 
    c.releaseTimestamp DESC,
    c.date             DESC,
    c.areaType         ASC,
    c.areaNameLower    ASC\
""")


LatestTransmissionRate = """\
SELECT TOP 1
    c.transmissionRateMin,
    c.transmissionRateMax,
    c.transmissionRateGrowthRateMin,
    c.transmissionRateGrowthRateMax,
    c.date
FROM     c
WHERE    c.releaseTimestamp = @releaseTimestamp
     AND c.areaNameLower    = @areaName
     AND IS_DEFINED(c.transmissionRateMin)
ORDER BY 
    c.releaseTimestamp DESC,
    c.date             DESC,
    c.areaType         ASC,
    c.areaNameLower    ASC\
"""


PostcodeLookup = """\
SELECT TOP 1 *
FROM     c
WHERE    c.type            = 'postcode'
     AND c.trimmedPostcode = @postcode\
"""


LookupByAreaCode = """\
SELECT TOP 1 c.areaName, c.destinations
FROM c
WHERE   c.type     = 'general'
    AND c.areaCode = @areaCode
    AND (
      (c.areaType = 'ltla' AND c.parent.areaCode != @areaCode)
      OR c.areaType = 'utla'
      OR c.areaTyoe = 'nhsTrust'
    )\
"""


DataByAreaCode = Template("""\
SELECT TOP 14 
    VALUE {
        'areaName': c.areaName,
        'areaType': c.areaType,
        'date':     c.date,
        'value':    c.$metric,
        'rate':     c.${metric}RollingRate ?? null
    }
FROM    c 
WHERE   
        c.releaseTimestamp = @releaseTimestamp
    AND c.areaType         = @areaType
    AND c.areaCode         = @areaCode
    AND IS_DEFINED(c.$metric)
ORDER BY 
    c.date DESC\
""")


SpecimenDateData = Template("""\
SELECT TOP 7
    VALUE {
        'date':         c.date,
        'value':        c.$metric,
        'rollingRate':  c.${metric}RollingRate ?? null,
        'rollingSum':   c.${metric}RollingSum  ?? null
    }
FROM    c 
WHERE   
        c.releaseTimestamp = @releaseTimestamp
    AND c.areaType         = @areaType
    AND c.areaCode         = @areaCode
    AND c.date            <= @latestDate
    AND IS_DEFINED(c.$metric)
ORDER BY 
    c.date DESC\
""")


SpecimenDateDataOverview = Template("""\
SELECT TOP 1
    VALUE {
        'date':        c.date,
        'value':       c.$metric,
        'rollingRate': c.${metric}RollingRate ?? null,
        'rollingSum':  c.${metric}RollingSum  ?? null
    }
FROM    c 
WHERE   
        c.releaseTimestamp = @releaseTimestamp
    AND c.areaType         = @areaType
    AND c.date            <= @latestDate
    AND IS_DEFINED(c.$metric)
ORDER BY 
    c.date DESC\
""")


MsoaData = """\
SELECT VALUE udf.cleanData(c) 
FROM c 
WHERE c.id = @id\
"""


AlertLevel = """\
SELECT TOP 1 VALUE udf.processAlertLevel(c)
FROM c 
WHERE 
      c.releaseTimestamp = @releaseTimestamp
  AND c.areaType         = @areaType
  AND c.areaCode         = @areaCode
  AND IS_DEFINED(c.alertLevel)
ORDER BY 
    c.date DESC\
"""


LatestChangeData = Template("""\
SELECT TOP 1
    VALUE {
        'date':              c.date,
        'value':             c.$metric,
        'change':            c.${metric}Change ?? null,
        'changePercentage':  c.${metric}ChangePercentage  ?? null,
        'rollingSum':        c.${metric}RollingSum ?? null,
        'changeDirection':   c.${metric}Direction = 'UP' 
                                 ? 0 
                                 : c.${metric}Direction = 'DOWN' 
                                 ? 180 
                                 : 90
    }
FROM    c 
WHERE   
        c.releaseTimestamp = @releaseTimestamp
    AND c.areaType         = @areaType
    AND c.areaCode         = @areaCode
    AND c.date            <= @latestDate
    AND IS_DEFINED(c.$metric)
ORDER BY 
    c.date DESC\
""")

LatestChangeDataOverview = Template("""\
SELECT TOP 1
    VALUE {
        'date':             c.date,
        'value':            c.$metric,
        'change':           c.${metric}Change ?? null,
        'changePercentage': c.${metric}ChangePercentage  ?? null,
        'rollingSum':       c.${metric}RollingSum ?? null,
        'changeDirection':  c.${metric}Direction = 'UP' 
                                ? 0 
                                : c.${metric}Direction = 'DOWN' 
                                ? 180 
                                : 90
    }
FROM    c 
WHERE   
        c.releaseTimestamp = @releaseTimestamp
    AND c.areaType         = @areaType
    AND c.date            <= @latestDate
    AND IS_DEFINED(c.$metric)
ORDER BY 
    c.date DESC\
""")


HealthCheck = """\
SELECT TOP 1 *
FROM c 
WHERE c.type = 'general'\
"""


Vaccinations = """\
SELECT TOP 1 VALUE {
        'date': c.date,
        'cumPeopleReceivingFirstDose': c.cumPeopleVaccinatedFirstDoseByVaccinationDate,
        'cumPeopleReceivingSecondDose': c.cumPeopleVaccinatedSecondDoseByVaccinationDate
    }
FROM c 
WHERE    c.releaseTimestamp = @releaseTimestamp
     AND c.areaNameLower    = @areaName
     AND IS_DEFINED(c.cumPeopleVaccinatedFirstDoseByVaccinationDate)
ORDER BY 
    c.date DESC\
"""
