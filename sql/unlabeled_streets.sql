-- The evidence for WHY boroughs go missing: the unlabeled rows concentrate on
-- limited-access highways, outside precinct street-grid geocoding.
SELECT
    trim(on_street_name)                AS street,
    count(*)                            AS crashes,
    sum(number_of_persons_killed)       AS killed
FROM crashes_filtered
WHERE borough IS NULL AND on_street_name IS NOT NULL
GROUP BY street
ORDER BY crashes DESC
LIMIT 10;
