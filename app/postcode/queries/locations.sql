SELECT id, ref.area_type, area_name, postcode, priority
FROM covid19.postcode_lookup
    JOIN covid19.area_reference AS ref ON ref.id = area_id
    JOIN covid19.area_priorities AS ap ON ap.area_type = ref.area_type
WHERE UPPER(REPLACE(postcode, ' ', '')) = $1;
