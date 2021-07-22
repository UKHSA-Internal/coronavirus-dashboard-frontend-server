SELECT cl.id::TEXT,
	   cl.date,
       cl.high_priority,
       t.tag           AS type,
       cl.heading,
       cl.body         AS body
FROM covid19.change_log AS cl
  LEFT JOIN covid19.tag                  AS t ON t.id = cl.type_id
  LEFT JOIN covid19.change_log_to_page   AS cltp ON cltp.log_id = cl.id
  LEFT JOIN covid19.page                 AS p ON p.id = cltp.page_id
WHERE cl.display_banner IS TRUE
  AND date = $1::DATE
  AND (
	   cl.area ISNULL
	OR cl.area @> '{overview::^K.*$}'::VARCHAR[]
    )
ORDER BY date DESC;