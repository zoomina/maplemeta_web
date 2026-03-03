SELECT
    job_name,
    AVG(CASE WHEN floor >= 50 THEN 1.0 ELSE 0.0 END) AS floor50_rate
FROM dm.dm_rank
GROUP BY job_name;
