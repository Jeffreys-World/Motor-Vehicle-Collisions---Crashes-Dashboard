-- Every fatal crash, plus a bounded sample of the rest. Fatal crashes are 0.16%
-- of the table, so an unweighted sample would render almost none of them and the
-- chart would say nothing about severity.
SELECT latitude, longitude, crash_date,
       number_of_persons_injured AS injured,
       number_of_persons_killed  AS killed,
       on_street_name            AS street,
       borough
FROM crashes_filtered
WHERE has_valid_location AND number_of_persons_killed > 0
UNION ALL
SELECT latitude, longitude, crash_date,
       number_of_persons_injured, number_of_persons_killed,
       on_street_name, borough
FROM crashes_filtered
WHERE has_valid_location AND number_of_persons_killed = 0
  AND number_of_persons_injured > 0
USING SAMPLE 4000 ROWS;
