import os
import pandas as pd
import psycopg2
import streamlit as st
import plotly.express as px
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

def qdf(sql, params=None):
    with conn() as c:
        return pd.read_sql(sql, c, params=params)

st.set_page_config(page_title="Temperature Ops Dashboard", layout="wide")
st.title(" Industrial Temperature Operations Dashboard")
st.caption("Historian-style trends + KPIs + overheat detection + missing-data monitoring")

# ---- Filters (Site → Area → Unit → Equipment → Tag) ----
sites = qdf("SELECT site_id, name FROM site ORDER BY name")
site_name = st.sidebar.selectbox("Site", sites["name"].tolist())
site_id = int(sites.loc[sites["name"] == site_name, "site_id"].iloc[0])

areas = qdf("SELECT area_id, name FROM area WHERE site_id=%s ORDER BY name", (site_id,))
area_name = st.sidebar.selectbox("Area", areas["name"].tolist())
area_id = int(areas.loc[areas["name"] == area_name, "area_id"].iloc[0])

units = qdf("SELECT unit_id, name FROM unit WHERE area_id=%s ORDER BY name", (area_id,))
unit_name = st.sidebar.selectbox("Unit", units["name"].tolist())
unit_id = int(units.loc[units["name"] == unit_name, "unit_id"].iloc[0])

eqs = qdf("SELECT equipment_id, name FROM equipment WHERE unit_id=%s ORDER BY name", (unit_id,))
eq_name = st.sidebar.selectbox("Equipment", eqs["name"].tolist())
eq_id = int(eqs.loc[eqs["name"] == eq_name, "equipment_id"].iloc[0])

tags = qdf("""
  SELECT tag_id, attribute_name, tag_name, uom
  FROM tag
  WHERE equipment_id=%s AND enabled=TRUE
  ORDER BY attribute_name
""", (eq_id,))

tag_label = st.sidebar.selectbox(
    "Temperature Tag",
    (tags["attribute_name"] + "  (" + tags["uom"] + ")").tolist()
)
tag_row = tags.iloc[(tags["attribute_name"] + "  (" + tags["uom"] + ")").tolist().index(tag_label)]
tag_id = int(tag_row["tag_id"])

range_choice = st.sidebar.selectbox("Trend range", ["1h", "6h", "24h", "7d"])
interval_map = {"1h": "1 hour", "6h": "6 hours", "24h": "24 hours", "7d": "7 days"}
interval = interval_map[range_choice]

# ---- KPI Tiles ----
kpi = qdf("""
SELECT
  t.tag_name,
  l.latest_value,
  a.avg_1h,
  m.max_24h,
  r.missing_rate_1h
FROM tag t
LEFT JOIN v_tag_latest l ON l.tag_id = t.tag_id
LEFT JOIN v_tag_last_hour_avg a ON a.tag_id = t.tag_id
LEFT JOIN v_tag_24h_max m ON m.tag_id = t.tag_id
LEFT JOIN v_tag_missing_rate_1h r ON r.tag_id = t.tag_id
WHERE t.tag_id = %s
""", (tag_id,))

k = kpi.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Current", f"{(k.latest_value if pd.notna(k.latest_value) else '—')}")
c2.metric("Last-hour avg", f"{(round(k.avg_1h, 2) if pd.notna(k.avg_1h) else '—')}")
c3.metric("24h max", f"{(round(k.max_24h, 2) if pd.notna(k.max_24h) else '—')}")
c4.metric("Missing-data rate (1h)", f"{(round(k.missing_rate_1h*100, 1) if pd.notna(k.missing_rate_1h) else '—')}%")

st.divider()

# ---- Trend chart ----
df = qdf("""
SELECT ts, value
FROM temperature_reading
WHERE tag_id=%s AND ts >= NOW() - (%s)::interval
ORDER BY ts
""", (tag_id, interval))

if df.empty:
    st.warning("No data yet for this tag. Start the simulator.")
else:
    fig = px.line(df, x="ts", y="value", title=f"Trend: {tag_row['tag_name']}")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---- Active alarms (for selected equipment) ----
alarms = qdf("""
SELECT
  oe.event_id, t.tag_name, oe.start_ts, oe.max_value, oe.status
FROM overheat_event oe
JOIN tag t ON t.tag_id = oe.tag_id
WHERE t.equipment_id = %s
ORDER BY oe.start_ts DESC
LIMIT 50
""", (eq_id,))

left, right = st.columns([2, 1])

with left:
    st.subheader(" Overheat Events (Equipment)")
    st.dataframe(alarms, use_container_width=True, hide_index=True)

with right:
    active = alarms[alarms["status"] == "ACTIVE"]
    st.subheader("Active Alerts")
    if active.empty:
        st.success("No active overheat alarms.")
    else:
        for _, row in active.iterrows():
            st.error(f"{row['tag_name']}\n\nSince: {row['start_ts']}\nMax: {row['max_value']}")
