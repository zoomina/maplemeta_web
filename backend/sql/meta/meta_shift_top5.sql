SELECT
    job_name,
    AVG(shift_score) AS score
FROM dm.dm_rank
WHERE floor >= 50
GROUP BY job_name
ORDER BY score DESC
LIMIT 5;
