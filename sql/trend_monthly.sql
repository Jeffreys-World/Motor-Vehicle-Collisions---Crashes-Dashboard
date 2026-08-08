SELECT
    crash_month                         AS month,
    count(*)                            AS crashes,
    sum(number_of_persons_injured)      AS injured,
    sum(number_of_persons_killed)       AS killed
FROM crashes_filtered
GROUP BY crash_month
ORDER BY crash_month;
