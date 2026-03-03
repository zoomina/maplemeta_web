SELECT
    job_name,
    type,
    floor,
    record_sec,
    floor / NULLIF(record_sec, 0) * 60.0 AS ter
FROM dm.dm_rank
WHERE floor BETWEEN 50 AND 69
  AND record_sec > 0
LIMIT 20000;
