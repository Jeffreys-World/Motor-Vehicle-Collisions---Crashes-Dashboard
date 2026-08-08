-- Crashes, injuries AND deaths together. A crash-volume line alone invites the
-- reading "NYC got 60% safer since 2019", which the fatality series refutes:
-- reported crashes fell 59.5% while deaths fell 6.1%.
SELECT
    crash_year                          AS year,
    count(*)                            AS crashes,
    sum(number_of_persons_injured)      AS injured,
    sum(number_of_persons_killed)       AS killed
FROM crashes_filtered
GROUP BY crash_year
ORDER BY crash_year;
