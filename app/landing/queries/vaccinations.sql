SELECT
     metric,
     date                        AS "date",
     (payload -> 'value')::FLOAT AS "value"
FROM covid19.time_series_p{partition} AS ts
JOIN covid19.release_reference AS rr ON rr.id = release_id
JOIN covid19.metric_reference  AS mr ON mr.id = metric_id
JOIN covid19.area_reference    AS ar ON ar.id = ts.area_id
WHERE
  area_type = 'overview'
  AND date >= '2020-04-01'
  AND metric IN (
        'cumVaccinationFirstDoseUptakeByPublishDatePercentage',
        'cumVaccinationSecondDoseUptakeByPublishDatePercentage'
    )
ORDER BY date DESC
FETCH FIRST 2 ROW ONLY;