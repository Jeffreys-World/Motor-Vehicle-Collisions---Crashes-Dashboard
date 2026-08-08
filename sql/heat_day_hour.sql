SELECT
    crash_dow                           AS dow,
    crash_dayname                       AS dayname,
    crash_hour                          AS hour,
    count(*)                            AS crashes
FROM crashes_filtered
WHERE crash_datetime IS NOT NULL
GROUP BY crash_dow, crash_dayname, crash_hour
ORDER BY crash_dow, crash_hour;
