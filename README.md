# Industrial Temperature Operations Dashboard + Asset Hierarchy Template

Historian-style industrial temperature operations dashboard built with Python, PostgreSQL, and Streamlit.  
Includes an asset hierarchy template (site → area → unit → equipment → tag), KPI tiles (current, 1h avg, 24h max, missing-data rate), trend charts, and rule-based overheat event detection (threshold + duration).

---

## Features

### Historian-Style Dashboard
- Trend chart for a selected temperature tag (1h / 6h / 24h / 7d ranges)
- KPI tiles:
  - Current value (latest reading)
  - Last-hour average
  - 24-hour maximum
  - Missing-data rate (1 hour)

### Asset Hierarchy Template (Scales Across Assets)
- Models industrial structure:
  - Site → Area → Unit → Equipment → Tag(Attribute)
- Generates standardized historian-style tag names like:
  - `CALGARYPLANT.PROCESS.LINE1.EXTRUDER_01.BARREL_TEMP`

### Rule-Based Overheat Detection
- Detects overheating using:
  - `threshold_high` + `duration_seconds`
- Logs alarms as events in SQL:
  - ACTIVE when criteria met
  - CLEARED when conditions return to normal

### Repeatable Setup
- Seed new assets/tags by editing a single CSV template:
  - `data/asset_hierarchy_template.csv`

---

## Tech Stack
- Python (pandas, psycopg2, python-dotenv)
- PostgreSQL (Docker)
- Streamlit + Plotly
- SQL views for KPI rollups

---

## Project Structure

```
industrial-temp-dashboard/
  app/
    dashboard.py
  scripts/
    seed_assets.py
    simulate_stream.py
    detect_overheat.py
  sql/
    001_schema.sql
    002_views.sql
  data/
    asset_hierarchy_template.csv
  docker-compose.yml
  requirements.txt
  .env
```

---

## Getting Started

### 1) Prerequisites
- Python 3.10+
- Docker Desktop
- Windows PowerShell (or Bash)

### 2) Clone and install dependencies
```bash
git clone <your-repo-url>
cd industrial-temp-dashboard

python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Mac/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

---

## Database Setup (PostgreSQL via Docker)

### 3) Start Postgres
```bash
docker compose up -d
```

### Port note (Windows)
If you already have PostgreSQL installed locally, port 5432 may be in use.  
In that case, map Docker Postgres to 5433 instead.

Edit `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"
```

Restart:
```bash
docker compose down
docker compose up -d
```

### 4) Create `.env`
Create a file named `.env` in the project root.

If using port 5432:
```env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=tempops
DB_USER=tempops
DB_PASSWORD=tempops
```

If using port 5433:
```env
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=tempops
DB_USER=tempops
DB_PASSWORD=tempops
```

### 5) Apply schema and KPI views

PowerShell-friendly commands:
```powershell
Get-Content .\sql\001_schema.sql -Raw | docker exec -i tempops_db psql -U tempops -d tempops
Get-Content .\sql\002_views.sql  -Raw | docker exec -i tempops_db psql -U tempops -d tempops
```

Verify tables:
```powershell
docker exec -it tempops_db psql -U tempops -d tempops -c "\dt"
```

---

## Seed Assets (Hierarchy + Tags)

### 6) Edit the template CSV
`data/asset_hierarchy_template.csv` controls what appears in the dashboard.

Example:
```csv
site,area,unit,equipment,attribute_name,uom,threshold_high,duration_seconds
CalgaryPlant,Process,Line1,Extruder-01,barrel_temp,C,210,180
```

### 7) Seed into the database
```bash
python .\scripts\seed_assets.py
```

Verify tags:
```powershell
docker exec -it tempops_db psql -U tempops -d tempops -c "SELECT tag_name, threshold_high FROM tag;"
```

---

## Generate Data and Detect Overheat

### 8) Start the simulator (time-series readings)
In one terminal:
```bash
python .\scripts\simulate_stream.py
```

This simulates historian-style values using a random-walk with occasional spikes.

### 9) Run overheat detection (every minute)
In another terminal (PowerShell loop):
```powershell
while ($true) { python .\scripts\detect_overheat.py; Start-Sleep -Seconds 60 }
```

---

## Run the Dashboard

### 10) Launch Streamlit
```bash
python -m streamlit run .\app\dashboard.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

---

## KPI Definitions
- Current: latest reading for the selected tag
- Last-hour avg: average value over the last 60 minutes
- 24h max: maximum value over the last 24 hours
- Missing-data rate (1 hour):
  - expected points = 60/hour (assumes one point per minute)
  - missing rate = (expected - actual) / expected

If you change the simulator interval (e.g., one point per 10 seconds), update the expected points accordingly.

---

## Overheat Detection Logic
A tag triggers an ACTIVE overheat event when:
- `value >= threshold_high` continuously for `duration_seconds`

It is CLEARED when:
- there are no over-threshold readings in a recent cooldown window

Events are stored in `overheat_event` for audit and reporting.

---

## Troubleshooting

### Streamlit command not found
Run:
```bash
python -m streamlit run .\app\dashboard.py
```

### Password authentication failed
You may be connecting to a different local PostgreSQL instance on port 5432.
- Map Docker Postgres to 5433
- Update `.env` to match

Check port usage:
```powershell
netstat -aon | findstr :5432
```

### Missing-data rate is high
This usually means:
- the simulator just started, or
- the expected frequency (60/hour) does not match the simulator interval.

---

## Future Improvements
- TimescaleDB hypertables for time-series performance
- Downsampling views (1m/5m/1h rollups)
- Plant overview page (hottest assets, alarms by area)
- Multi-tag overlays (bearing vs motor temp)
- Alert routing and acknowledgement workflow

---
