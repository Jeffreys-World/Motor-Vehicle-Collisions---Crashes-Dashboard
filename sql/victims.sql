-- Unpivoted rather than three separate scalars, so the chart reads as one
-- comparable population.
SELECT 'Motorists'   AS victim_type,
       sum(number_of_motorist_injured)   AS injured,
       sum(number_of_motorist_killed)    AS killed FROM crashes_filtered
UNION ALL
SELECT 'Pedestrians',
       sum(number_of_pedestrians_injured),
       sum(number_of_pedestrians_killed) FROM crashes_filtered
UNION ALL
SELECT 'Cyclists',
       sum(number_of_cyclist_injured),
       sum(number_of_cyclist_killed)     FROM crashes_filtered;
