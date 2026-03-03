SELECT
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'dm'
ORDER BY table_name
LIMIT 100;
