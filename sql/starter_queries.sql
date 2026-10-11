-- Optional MySQL starter queries after importing real observations into heat_observations.
SELECT area, AVG(temperature_c) AS mean_temp_c, MIN(temperature_c) AS min_temp_c,
       MAX(temperature_c) AS max_temp_c, COUNT(*) AS observation_count
FROM heat_observations
GROUP BY area
ORDER BY mean_temp_c DESC;

SELECT DATE(observation_date) AS observation_day, area, AVG(temperature_c) AS mean_temp_c
FROM heat_observations
GROUP BY DATE(observation_date), area
ORDER BY observation_day, area;

SELECT COUNT(*) AS total_rows,
       SUM(temperature_c IS NULL) AS missing_temperature,
       SUM(vegetation_pct IS NULL) AS missing_vegetation,
       SUM(built_up_pct IS NULL) AS missing_built_up
FROM heat_observations;
