-- AGGREGATED into a grid, never raw points. 848k markers hangs the browser,
-- which is a separate limit from the container's ~1GB ceiling.
SELECT
    round(latitude,  3)                 AS lat_bin,
    round(longitude, 3)                 AS lon_bin,
    count(*)                            AS crashes,
    sum(number_of_persons_killed)       AS killed
FROM crashes_filtered
WHERE has_valid_location
GROUP BY lat_bin, lon_bin
HAVING count(*) > 1
ORDER BY crashes DESC;
