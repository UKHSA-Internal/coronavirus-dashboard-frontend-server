SELECT
    *
FROM (
    SELECT area_code    AS "areaCode",
         MAX(area_type) AS "areaType",
         MAX(area_name) AS "areaName",
         MAX(date)      AS "date",
         metric,
         MAX(
             CASE
                WHEN (payload ->> 'value')::TEXT = 'UP'   THEN 0
                WHEN (payload ->> 'value')::TEXT = 'DOWN' THEN 180
                WHEN (payload ->> 'value')::TEXT = 'SAME' THEN 90
                ELSE (payload ->> 'value')::NUMERIC
            END
         ) AS value,
         RANK() OVER (
            PARTITION BY (metric)
            ORDER BY date DESC
         ) AS rank
    FROM covid19.time_series_p{partition}   AS main
    JOIN covid19.release_reference AS rr ON rr.id = release_id
    JOIN covid19.metric_reference  AS mr ON mr.id = metric_id
    JOIN covid19.area_reference    AS ar ON ar.id = main.area_id
    WHERE
          area_type = 'overview'
      AND date > ( DATE($1) - INTERVAL '8 days' )
      AND metric = ANY( $2::VARCHAR[] )
    GROUP BY area_type, area_code, date, metric
) AS result
WHERE result.rank = 1;
