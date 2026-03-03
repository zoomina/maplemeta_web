SELECT
    job_name,
    type,
    floor
FROM dm.dm_rank
WHERE floor IS NOT NULL
LIMIT 20000;
