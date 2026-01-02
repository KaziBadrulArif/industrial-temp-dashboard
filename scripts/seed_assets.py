import os
import pandas as pd
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

def upsert(cur, sql, params):
    cur.execute(sql, params)
    return cur.fetchone()[0]

def make_tag_name(site, area, unit, equipment, attr):
    # historian-style tag naming standard
    def clean(s): return str(s).strip().replace(" ", "_").replace("-", "_")
    return f"{clean(site)}.{clean(area)}.{clean(unit)}.{clean(equipment)}.{clean(attr)}".upper()

def main():
    df = pd.read_csv("data/asset_hierarchy_template.csv")
    with conn() as c:
        with c.cursor() as cur:
            for _, r in df.iterrows():
                site_id = upsert(cur,
                    "INSERT INTO site(name) VALUES(%s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name RETURNING site_id",
                    (r["site"],)
                )
                area_id = upsert(cur,
                    "INSERT INTO area(site_id,name) VALUES(%s,%s) ON CONFLICT(site_id,name) DO UPDATE SET name=EXCLUDED.name RETURNING area_id",
                    (site_id, r["area"])
                )
                unit_id = upsert(cur,
                    "INSERT INTO unit(area_id,name) VALUES(%s,%s) ON CONFLICT(area_id,name) DO UPDATE SET name=EXCLUDED.name RETURNING unit_id",
                    (area_id, r["unit"])
                )
                eq_id = upsert(cur,
                    "INSERT INTO equipment(unit_id,name) VALUES(%s,%s) ON CONFLICT(unit_id,name) DO UPDATE SET name=EXCLUDED.name RETURNING equipment_id",
                    (unit_id, r["equipment"])
                )

                tag_name = make_tag_name(r["site"], r["area"], r["unit"], r["equipment"], r["attribute_name"])

                cur.execute("""
                    INSERT INTO tag(equipment_id, attribute_name, uom, tag_name, threshold_high, duration_seconds)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(tag_name) DO UPDATE SET
                      threshold_high = EXCLUDED.threshold_high,
                      duration_seconds = EXCLUDED.duration_seconds,
                      enabled = TRUE
                """, (eq_id, r["attribute_name"], r["uom"], tag_name, float(r["threshold_high"]), int(r["duration_seconds"])))

        c.commit()

    print(" Seeded hierarchy + tags from template.")

if __name__ == "__main__":
    main()
