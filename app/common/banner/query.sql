WITH latest_release AS (
    SELECT MAX(rr.timestamp)::DATE
    FROM covid19.release_reference AS rr
    WHERE rr.released IS TRUE
)
SELECT id::TEXT,
       launch::DATE,
       expire::DATE,
       COALESCE(date, launch::DATE) AS date,
       body
FROM covid19.announcement AS an
WHERE
    (
        (
                an.deploy_with_release IS TRUE
            AND an.launch::DATE <= (SELECT * FROM latest_release)
        )
      OR (
                an.deploy_with_release IS FALSE
            AND an.launch <= NOW()
        )
    )
  AND (
        (
                an.remove_with_release IS TRUE
            AND an.expire::DATE > (SELECT * FROM latest_release)
        )
      OR (
                an.remove_with_release IS FALSE
            AND an.expire > NOW()
        )
    )
ORDER BY an.launch DESC, an.expire DESC;
