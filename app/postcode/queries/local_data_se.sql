CREATE TEMPORARY TABLE data AS (
    SELECT *
    FROM (
             SELECT hash,
                    metric,
                    priority,
                    area_code AS area_code,
                    postcode  AS postcode,
                    area_type AS area_type,
                    area_name AS area_name,
                    date      AS date,
                    payload
             FROM covid19.time_series_p{partition_date}_other AS ts
                      JOIN covid19.release_reference AS rr ON rr.id = release_id
                      JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                      JOIN (
                 SELECT id, ref.area_type, area_code, area_name, postcode, priority
                 FROM covid19.postcode_lookup_reference
                          JOIN covid19.area_reference AS ref ON ref.id = area_id
                          JOIN covid19.area_priorities AS ap ON ref.area_type = ap.area_type
                 WHERE UPPER(REPLACE(postcode, ' ', '')) = $2
             ) AS location ON location.id = area_id
             WHERE rr.released IS TRUE
               AND metric ILIKE ANY ($1::VARCHAR[])
             UNION ALL
             (
                 SELECT hash,
                        metric,
                        priority,
                        area_code AS area_code,
                        postcode  AS postcode,
                        area_type AS area_type,
                        area_name AS area_name,
                        date      AS date,
                        payload
                 FROM covid19.time_series_p{partition_date}_utla AS ts
                          JOIN covid19.release_reference AS rr ON rr.id = release_id
                          JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                          JOIN (
                     SELECT id, ref.area_type, area_code, area_name, postcode, priority
                     FROM covid19.postcode_lookup_reference
                              JOIN covid19.area_reference AS ref ON ref.id = area_id
                              JOIN covid19.area_priorities AS ap ON ref.area_type = ap.area_type
                     WHERE UPPER(REPLACE(postcode, ' ', '')) = $2
                 ) AS location ON location.id = area_id
                 WHERE rr.released IS TRUE
                   AND metric ILIKE ANY ($1::VARCHAR[])

             )
             UNION ALL
             (
                 SELECT hash,
                        metric,
                        priority,
                        area_code AS area_code,
                        postcode  AS postcode,
                        area_type AS area_type,
                        area_name AS area_name,
                        date      AS date,
                        payload
                 FROM covid19.time_series_p{partition_date}_ltla AS ts
                          JOIN covid19.release_reference AS rr ON rr.id = release_id
                          JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                          JOIN (
                     SELECT id, ref.area_type, area_code, area_name, postcode, priority
                     FROM covid19.postcode_lookup_reference
                              JOIN covid19.area_reference AS ref ON ref.id = area_id
                              JOIN covid19.area_priorities AS ap ON ref.area_type = ap.area_type
                     WHERE UPPER(REPLACE(postcode, ' ', '')) = $2
                 ) AS location ON location.id = area_id
                 WHERE rr.released IS TRUE
                   AND metric ILIKE ANY ($1::VARCHAR[])
             )
             UNION ALL
             (
                 SELECT hash,
                        metric,
                        priority,
                        area_code AS area_code,
                        postcode  AS postcode,
                        area_type AS area_type,
                        area_name AS area_name,
                        date      AS date,
                        payload
                 FROM covid19.time_series_p{partition_date}_nhstrust AS ts
                          JOIN covid19.release_reference AS rr ON rr.id = release_id
                          JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                          JOIN (
                     SELECT id, ref.area_type, area_code, area_name, postcode, priority
                     FROM covid19.postcode_lookup_reference
                              JOIN covid19.area_reference AS ref ON ref.id = area_id
                              JOIN covid19.area_priorities AS ap ON ref.area_type = ap.area_type
                     WHERE UPPER(REPLACE(postcode, ' ', '')) = $2
                 ) AS location ON location.id = area_id
                 WHERE rr.released IS TRUE
                   AND metric ILIKE ANY ($1::VARCHAR[])
             )
         ) as f
);

CREATE TEMPORARY TABLE msoa AS (
    SELECT area_code,
           postcode,
           area_type,
           area_name,
           date,
           metric,
           key,
           value,
           priority
    FROM covid19.time_series_p{partition_date}_msoa AS ts
             JOIN covid19.release_reference AS rr ON rr.id = release_id
             JOIN covid19.metric_reference AS mr ON mr.id = metric_id
             JOIN (
        SELECT id, ref.area_type, area_code, area_name, postcode, priority
        FROM covid19.postcode_lookup_reference
                 JOIN covid19.area_reference AS ref ON ref.id = area_id
                 JOIN covid19.area_priorities AS ap ON ref.area_type = ap.area_type
        WHERE UPPER(REPLACE(postcode, ' ', '')) = $2
    ) AS location ON location.id = area_id,
         jsonb_each(payload) AS pa
    WHERE rr.released IS TRUE
      AND metric ILIKE ANY ($1::VARCHAR[])
    OFFSET 0
);

SELECT "areaCode",
       postcode,
       "areaType",
       "areaName",
       date,
       metric,
       value,
       priority
FROM (
         SELECT area_code AS "areaCode",
                postcode,
                area_type AS "areaType",
                area_name AS "areaName",
                date,
                metric,
                (
                    CASE
                        WHEN value::TEXT = 'UP' THEN 0
                        WHEN value::TEXT = 'DOWN' THEN 180
                        WHEN value::TEXT = 'SAME' THEN 90
                        WHEN area_type = 'msoa' AND metric LIKE $1 THEN value::NUMERIC
                        WHEN metric ILIKE ANY ($2::VARCHAR[]) THEN value::NUMERIC
                        ELSE round(value::NUMERIC)::INT
                        END
                    )     AS "value",
                priority
         FROM (
                  SELECT metric,
                         priority,
                         area_code                   AS area_code,
                         postcode                    AS postcode,
                         area_type                   AS area_type,
                         area_name                   AS area_name,
                         date                        AS date,
                         (payload ->> 'value')::TEXT AS "value",
                         RANK() OVER (
                             PARTITION BY (metric)
                             ORDER BY priority, date DESC
                             )                       AS rank
                  FROM (SELECT * FROM data OFFSET 0) AS t

                  UNION ALL
                  (
                      SELECT (metric || UPPER(LEFT(key, 1)) || RIGHT(key, -1)) AS metric,
                             1                                                 AS priority,
                             area_code,
                             postcode,
                             area_type,
                             area_name,
                             date,
                             (
                                 CASE
                                     WHEN value::TEXT <> 'null' THEN TRIM(BOTH '"' FROM value::TEXT)
                                     WHEN value::TEXT = 'null' THEN '-999999'
                                     END
                                 )                                             AS value,
                             RANK() OVER (
                                 PARTITION BY (key)
                                 ORDER BY date DESC
                                 )                                             AS rank
                      FROM msoa
                  )
              ) AS result_inner
         WHERE result_inner.rank = 1
     ) AS result;