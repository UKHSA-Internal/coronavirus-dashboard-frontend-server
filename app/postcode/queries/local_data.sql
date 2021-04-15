WITH
     location AS (
        SELECT id, ref.area_type, area_code, area_name, postcode, priority
        FROM covid19.postcode_lookup
            JOIN covid19.area_reference  AS ref ON ref.id = area_id
            JOIN covid19.area_priorities AS ap  ON ref.area_type = ap.area_type
        WHERE UPPER(REPLACE(postcode, ' ', '')) = $2
    ),
     metrics AS (
        SELECT id, metric
        FROM covid19.metric_reference
        WHERE metric ILIKE ANY($1::VARCHAR[])
    ),
    data AS (
        -- Subquery necessary to push jobs to worker nodes.
        SELECT * FROM (
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
                  JOIN metrics ON metrics.id = metric_id
                  JOIN location ON location.id = ts.area_id
              WHERE released IS TRUE
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
                      JOIN metrics ON metrics.id = metric_id
                      JOIN location ON location.id = ts.area_id
                  WHERE released IS TRUE
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
                      JOIN metrics ON metrics.id = metric_id
                      JOIN location ON location.id = ts.area_id
                  WHERE released IS TRUE
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
                      JOIN metrics ON metrics.id = metric_id
                      JOIN location ON location.id = ts.area_id
                  WHERE released IS TRUE
              )
        ) AS main_metrics
    ),
     msoa AS (
        SELECT area_code, postcode, area_type, area_name, date, metric, payload, priority
         FROM covid19.time_series_p{partition_date}_msoa AS ts
             JOIN covid19.release_reference AS rr ON rr.id = release_id
             JOIN metrics ON metrics.id = ts.metric_id
             JOIN location AS ref ON ref.id = ts.area_id
         WHERE released IS TRUE
         OFFSET 0  -- offset necessary to push jobs down to worker nodes.
    )
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
                WHEN area_type = 'msoa' AND metric LIKE $3 THEN value::NUMERIC
                WHEN metric ILIKE ANY ($4::VARCHAR[]) THEN value::NUMERIC
                ELSE round( value::NUMERIC )::INT
            END
        ) AS "value",
        priority,
        RANK() OVER (
            PARTITION BY ( metric )
            ORDER BY priority
        ) AS rank
    FROM (
        SELECT metric,
               priority,
               area_code AS area_code,
               postcode  AS postcode,
               area_type AS area_type,
               area_name AS area_name,
               date      AS date,
               (payload ->> 'value')::TEXT AS "value",
               -- Do not move to the CTE. Doing so will cause the jobs
               -- to run on the coordinator.
               RANK() OVER (
                   PARTITION BY (metric)
                   ORDER BY priority, date DESC
               ) AS rank
        FROM (
            -- Subquery + offset necessary to push jobs to worker nodes.
            SELECT * FROM data OFFSET 0
        ) AS main_inner
        UNION ALL (
            SELECT (metric || UPPER(LEFT(key, 1)) || RIGHT(key, -1)) AS metric,
                   1 AS priority,
                   area_code,
                   postcode,
                   area_type,
                   area_name,
                   date,
                   (
                       CASE
                           WHEN value::TEXT <> 'null' THEN TRIM( BOTH '"' FROM value::TEXT )
                           ELSE '-999999'
                       END
                   ) AS value,
                   RANK() OVER (
                       PARTITION BY ( key )
                           ORDER BY date DESC
                   ) AS rank
            FROM msoa,
                 -- Do not move to CTE - doing so will prolong execution.
                 jsonb_each(payload) AS pa
        )
    ) AS result_inner
    WHERE result_inner.rank = 1
) AS result
WHERE result.rank = 1;
