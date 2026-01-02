-- Asset hierarchy
CREATE TABLE IF NOT EXISTS site (
  site_id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS area (
  area_id SERIAL PRIMARY KEY,
  site_id INT NOT NULL REFERENCES site(site_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  UNIQUE(site_id, name)
);

CREATE TABLE IF NOT EXISTS unit (
  unit_id SERIAL PRIMARY KEY,
  area_id INT NOT NULL REFERENCES area(area_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  UNIQUE(area_id, name)
);

CREATE TABLE IF NOT EXISTS equipment (
  equipment_id SERIAL PRIMARY KEY,
  unit_id INT NOT NULL REFERENCES unit(unit_id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  UNIQUE(unit_id, name)
);

-- Attribute/Tag definition (e.g., "bearing_temp", "motor_temp")
CREATE TABLE IF NOT EXISTS tag (
  tag_id SERIAL PRIMARY KEY,
  equipment_id INT NOT NULL REFERENCES equipment(equipment_id) ON DELETE CASCADE,
  attribute_name TEXT NOT NULL,          -- e.g. "bearing_temp"
  uom TEXT NOT NULL DEFAULT 'C',         -- units
  tag_name TEXT UNIQUE NOT NULL,         -- historian-style tag: SITE.AREA.UNIT.EQ.ATTR
  threshold_high DOUBLE PRECISION,       -- overheat threshold
  duration_seconds INT NOT NULL DEFAULT 300, -- threshold must hold for this long
  enabled BOOLEAN NOT NULL DEFAULT TRUE
);

-- Time-series temperature readings
CREATE TABLE IF NOT EXISTS temperature_reading (
  reading_id BIGSERIAL PRIMARY KEY,
  tag_id INT NOT NULL REFERENCES tag(tag_id) ON DELETE CASCADE,
  ts TIMESTAMPTZ NOT NULL,
  value DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_temp_tag_ts ON temperature_reading(tag_id, ts DESC);

-- Overheat events
CREATE TABLE IF NOT EXISTS overheat_event (
  event_id BIGSERIAL PRIMARY KEY,
  tag_id INT NOT NULL REFERENCES tag(tag_id) ON DELETE CASCADE,
  start_ts TIMESTAMPTZ NOT NULL,
  end_ts TIMESTAMPTZ,
  max_value DOUBLE PRECISION NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE'  -- ACTIVE / CLEARED
);

CREATE INDEX IF NOT EXISTS idx_overheat_tag_status ON overheat_event(tag_id, status);
