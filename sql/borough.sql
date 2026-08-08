-- The chart this project exists to criticise. Reports the unlabeled bucket as a
-- first-class row instead of dropping it, and carries deaths so the rate is
-- visible rather than implied.
SELECT
    coalesce(borough, '(no borough recorded)')  AS borough,
    (borough IS NULL)                           AS is_unlabeled,
    count(*)                                    AS crashes,
    sum(number_of_persons_injured)              AS injured,
    sum(number_of_persons_killed)               AS killed
FROM crashes_filtered
GROUP BY borough
ORDER BY crashes DESC;
