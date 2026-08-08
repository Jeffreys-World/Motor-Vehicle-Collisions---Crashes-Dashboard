-- Headline counters. Deliberately includes the unlabeled-borough split, because
-- that gap is the point of the project rather than a footnote.
SELECT
    count(*)                                                   AS crashes,
    sum(number_of_persons_injured)                             AS injured,
    sum(number_of_persons_killed)                              AS killed,
    count(*) FILTER (WHERE borough IS NULL)                     AS unlabeled_crashes,
    sum(number_of_persons_killed) FILTER (WHERE borough IS NULL) AS unlabeled_killed
FROM crashes_filtered;
