SELECT area_code AS "areaCode",
       area_type AS "areaType",
       area_name AS "areaName",
       date,
       metric,
       (
           CASE
               WHEN value::TEXT = 'UP' THEN 0
               WHEN value::TEXT = 'DOWN' THEN 180
               WHEN value::TEXT = 'SAME' THEN 90
               WHEN metric LIKE 'newCasesBySpecimenDate%' THEN value::NUMERIC
               ELSE round(value::NUMERIC)::INT
               END
       )     AS value,
       priority
FROM (
         SELECT (metric || UPPER(LEFT(key, 1)) || RIGHT(key, -1)) AS metric,
                1 AS priority,
                area_code     AS area_code,
                ref.area_type AS area_type,
                area_name     AS area_name,
                date          AS date,
                (
                    CASE
                        WHEN value::TEXT <> 'null' THEN TRIM(BOTH '"' FROM value::TEXT)
                        ELSE '-999999'
                        END
                )         AS value,
                RANK() OVER (
                    PARTITION BY (metric)
                    ORDER BY date DESC
                )         AS rank
         FROM covid19.time_series_p{partition_id} AS ts
             JOIN covid19.release_reference AS rr
         ON rr.id = release_id
             JOIN covid19.metric_reference AS mr ON mr.id = metric_id
             JOIN covid19.area_reference AS ref ON ref.id = area_id,
                jsonb_each(payload) AS pa
         WHERE rr.released IS TRUE
           AND ref.id = $1
           AND metric ILIKE ANY($2::VARCHAR[])
     ) AS ts
WHERE ts.metric ILIKE ANY($3::VARCHAR[])
AND ts.rank = 1;
