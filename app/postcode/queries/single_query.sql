SELECT area_code AS "areaCode",
       area_type AS "areaType",
       area_name AS "areaName",
       date,
       metric,
       value,
       priority
FROM (
         SELECT metric,
                priority,
                area_code     AS area_code,
                ref.area_type AS area_type,
                area_name     AS area_name,
                date          AS date,
                (
                    CASE
                        WHEN (payload ->> 'value') = 'UP' THEN 0
                        WHEN (payload ->> 'value') = 'DOWN' THEN 180
                        WHEN (payload ->> 'value') = 'SAME' THEN 90
                        WHEN (ref.area_type = 'msoa' AND metric LIKE 'newCasesBySpecimenDate%')
                            OR metric ILIKE ANY ($1::VARCHAR[]) THEN (payload -> 'value')::NUMERIC
                        ELSE round((payload -> 'value')::NUMERIC)::INT
                        END
                )         AS "value",
                RANK() OVER (
                    PARTITION BY (metric)
                    ORDER BY priority, date DESC
                )         AS rank
         FROM covid19.time_series_p{partition_id} AS ts
             JOIN covid19.release_reference AS rr ON rr.id = release_id
             JOIN covid19.metric_reference  AS mr ON mr.id = metric_id
             JOIN covid19.area_reference    AS ref ON ref.id = area_id
             JOIN covid19.area_priorities   AS ap ON ref.area_type = ap.area_type
         WHERE rr.released IS TRUE
           AND ref.id = $2
           AND metric ILIKE ANY ($3::VARCHAR[])
     ) AS ts
WHERE rank = 1;
