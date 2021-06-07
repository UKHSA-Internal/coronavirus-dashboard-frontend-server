SELECT
     metric,
     date                        AS "date",
     (payload -> 'value')::FLOAT AS "value"
FROM covid19.time_series_p{partition} AS ts
JOIN covid19.release_reference AS rr ON rr.id = release_id
JOIN covid19.metric_reference  AS mr ON mr.id = metric_id
JOIN covid19.area_reference    AS ar ON ar.id = ts.area_id
WHERE
      partition_id = $1
  AND area_type = 'overview'
  AND date > ( DATE( $2 ) - INTERVAL '30 days' )
  AND metric = $3
ORDER BY date DESC
OFFSET 0
FETCH FIRST 1 ROW ONLY;