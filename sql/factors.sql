SELECT
    contributing_factor_vehicle_1       AS factor,
    count(*)                            AS crashes,
    sum(number_of_persons_killed)       AS killed
FROM crashes_filtered
WHERE contributing_factor_vehicle_1 IS NOT NULL
GROUP BY factor
ORDER BY crashes DESC
LIMIT 12;
