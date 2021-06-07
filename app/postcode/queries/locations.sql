SELECT id, area_type, postcode
FROM covid19.postcode_lookup
    JOIN covid19.area_reference AS ref ON ref.id = area_id
WHERE UPPER(REPLACE(postcode, ' ', '')) = $1;
