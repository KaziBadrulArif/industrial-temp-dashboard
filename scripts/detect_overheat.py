import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

DETECT_SQL = """
WITH tag_cfg AS (
  SELECT tag_id, threshold_high, duration_seconds
  FROM tag
  WHERE enabled = TRUE AND threshold_high IS NOT NULL
),
recent AS (
  SELECT
    tr.tag_id,
    tr.ts,
    tr.value,
    tc.threshold_high,
    tc.duration_seconds
  FROM temperature_reading tr
  JOIN tag_cfg tc ON tc.tag_id = tr.tag_id
  WHERE tr.ts >= NOW() - INTERVAL '2 hours'
),
runs AS (
  SELECT
    r.*,
    (r.value >= r.threshold_high) AS is_hot,
    CASE WHEN r.value >= r.threshold_high THEN 0 ELSE 1 END AS cool_flag
  FROM recent r
),
grp AS (
  SELECT
    tag_id, ts, value, threshold_high, duration_seconds, is_hot,
    SUM(cool_flag) OVER (PARTITION BY tag_id ORDER BY ts) AS g
  FROM runs
),
hot_windows AS (
  SELECT
    tag_id,
    MIN(ts) AS start_ts,
    MAX(ts) AS end_ts,
    MAX(value) AS max_value,
    EXTRACT(EPOCH FROM (MAX(ts) - MIN(ts))) AS seconds_hot,
    MAX(duration_seconds) AS duration_seconds
  FROM grp
  WHERE is_hot = TRUE
  GROUP BY tag_id, g
),
violations AS (
  SELECT *
  FROM hot_windows
  WHERE seconds_hot >= duration_seconds
)
INSERT INTO overheat_event(tag_id, start_ts, max_value, status)
SELECT v.tag_id, v.start_ts, v.max_value, 'ACTIVE'
FROM violations v
WHERE NOT EXISTS (
  SELECT 1 FROM overheat_event oe
  WHERE oe.tag_id = v.tag_id AND oe.status = 'ACTIVE'
);
"""

CLEAR_SQL = """
UPDATE overheat_event oe
SET end_ts = NOW(), status = 'CLEARED'
WHERE oe.status = 'ACTIVE'
AND NOT EXISTS (
  SELECT 1
  FROM temperature_reading tr
  JOIN tag t ON t.tag_id = tr.tag_id
  WHERE tr.tag_id = oe.tag_id
    AND tr.ts >= NOW() - INTERVAL '10 minutes'
    AND tr.value >= t.threshold_high
);
"""

def main():
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(DETECT_SQL)
            cur.execute(CLEAR_SQL)
        c.commit()
    print("Overheat detection ran (new alarms inserted, old ones cleared if cooled).")

if __name__ == "__main__":
    main()
