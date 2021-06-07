SELECT
     date                           AS "date",
     (payload ->> 'value')::NUMERIC AS "value"
FROM covid19.time_series_p{partition} AS main
JOIN covid19.release_reference AS rr ON rr.id = release_id
JOIN covid19.metric_reference  AS mr ON mr.id = metric_id
JOIN covid19.area_reference    AS ar ON ar.id = main.area_id
WHERE
      partition_id = $1
  AND area_type = 'overview'
  AND date >= '2020-04-01'
  AND metric = $2
ORDER BY date DESC;
