SELECT "areaCode", postcode, "areaType", "areaName", date, metric, value, priority
FROM (
    SELECT
        area_code  AS "areaCode",
        postcode,
        area_type  AS "areaType",
        area_name  AS "areaName",
        date,
        metric,
        (
            CASE
                WHEN value::TEXT = 'UP'                    THEN 0
                WHEN value::TEXT = 'DOWN'                  THEN 180
                WHEN value::TEXT = 'SAME'                  THEN 90
                WHEN area_type = 'msoa' AND metric LIKE $5 THEN value::NUMERIC
                WHEN metric LIKE ANY ( $6::VARCHAR[] )     THEN value::NUMERIC
                ELSE round( value::NUMERIC )::INT
            END
        ) AS "value",
        priority,
        RANK() OVER (
            PARTITION BY ( metric )
            ORDER BY priority
        ) AS rank
    FROM (
        WITH location AS (
            SELECT id, ref.area_type, area_code, area_name, postcode, priority
            FROM covid19.postcode_lookup
            JOIN covid19.area_reference  AS ref ON ref.id = area_id
            JOIN covid19.area_priorities AS ap  ON ref.area_type = ap.area_type
            WHERE UPPER(REPLACE(postcode, ' ', '')) = $2
        )
        SELECT
           metric,
           priority,
           area_code                     AS area_code,
           postcode                      AS postcode,
           ref.area_type                 AS area_type,
           area_name                     AS area_name,
           date                          AS date,
           ( payload ->> 'value' )::TEXT AS "value",
           RANK() OVER (
               PARTITION BY ( metric )
               ORDER BY priority, date DESC
           ) AS rank
        FROM covid19.time_series       AS ts
        JOIN covid19.release_reference AS rr ON rr.id = release_id
        JOIN (
            SELECT id, metric
            FROM covid19.metric_reference
            WHERE metric = ANY($1::VARCHAR[])
         ) AS metrics ON metrics.id = metric_id
         JOIN location AS ref ON ref.id = ts.area_id
        WHERE partition_id = ANY($3::VARCHAR[])
        UNION (
            SELECT
                   (metric || UPPER(SUBSTRING(key FROM 1 FOR 1)) || SUBSTRING(key FROM 2)) AS metric,
                   1 AS priority,
                   area_code,
                   postcode,
                   area_type,
                   area_name,
                   date,
                   (
                        CASE
                            WHEN value::TEXT <> 'null' THEN TRIM( BOTH '"' FROM value::TEXT )
                            WHEN value::TEXT = 'null'  THEN '-999999'
                        END
                   ) AS value,
                   rank
            FROM (
                SELECT
                       area_code,
                       postcode,
                       ref.area_type,
                       area_name,
                       date,
                       metric,
                       ( jsonb_each(payload) ).*,
                       RANK() OVER (
                           PARTITION BY ( metric )
                           ORDER BY date DESC
                       ) AS rank
                FROM covid19.time_series_p{msoa_partition} AS ts
                JOIN covid19.release_reference AS rr ON rr.id = ts.release_id
                JOIN (
                    SELECT id, metric
                    FROM covid19.metric_reference
                    WHERE metric = $4
                 ) AS metrics ON metrics.id = ts.metric_id
                JOIN location AS ref ON ref.id = ts.area_id
            ) AS result_msoa
        )
    ) AS result_inner
    WHERE result_inner.rank = 1
) AS result
WHERE result.rank = 1;
