-- Last value per tag
CREATE OR REPLACE VIEW v_tag_latest AS
SELECT DISTINCT ON (tr.tag_id)
  tr.tag_id,
  tr.ts AS latest_ts,
  tr.value AS latest_value
FROM temperature_reading tr
ORDER BY tr.tag_id, tr.ts DESC;

-- Last hour average per tag
CREATE OR REPLACE VIEW v_tag_last_hour_avg AS
SELECT
  tag_id,
  AVG(value) AS avg_1h
FROM temperature_reading
WHERE ts >= NOW() - INTERVAL '1 hour'
GROUP BY tag_id;

-- 24 hour max per tag
CREATE OR REPLACE VIEW v_tag_24h_max AS
SELECT
  tag_id,
  MAX(value) AS max_24h
FROM temperature_reading
WHERE ts >= NOW() - INTERVAL '24 hours'
GROUP BY tag_id;

-- Missing data rate: expected points vs actual in last hour
-- Assumes we EXPECT one point per minute. Change expected_rate if you simulate differently.
CREATE OR REPLACE VIEW v_tag_missing_rate_1h AS
WITH actual AS (
  SELECT tag_id, COUNT(*) AS actual_points
  FROM temperature_reading
  WHERE ts >= NOW() - INTERVAL '1 hour'
  GROUP BY tag_id
),
expected AS (
  SELECT tag_id, 60 AS expected_points
  FROM tag
  WHERE enabled = TRUE
)
SELECT
  e.tag_id,
  COALESCE(a.actual_points, 0) AS actual_points,
  e.expected_points,
  (e.expected_points - COALESCE(a.actual_points, 0))::DOUBLE PRECISION / e.expected_points
    AS missing_rate_1h
FROM expected e
LEFT JOIN actual a ON a.tag_id = e.tag_id;
