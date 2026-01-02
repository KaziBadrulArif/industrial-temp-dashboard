import os, time, random
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

def conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

def main():
    interval_sec = 60  # one point per minute (matches missing rate assumption)
    print("📡 Simulating temperature stream... Ctrl+C to stop.")
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT tag_id, threshold_high FROM tag WHERE enabled = TRUE")
            tags = cur.fetchall()

        base = {tag_id: random.uniform(40, 70) for tag_id, _ in tags}

        try:
            while True:
                now = datetime.now(timezone.utc)
                with c.cursor() as cur:
                    for tag_id, threshold in tags:
                        # random walk + occasional spike to trigger alarms
                        drift = random.uniform(-0.8, 0.8)
                        spike = 0
                        if random.random() < 0.03:  # 3% chance spike
                            spike = random.uniform(10, 25)

                        base[tag_id] = max(0, base[tag_id] + drift + spike)

                        # keep around realistic band, unless spiking
                        if base[tag_id] < 20:
                            base[tag_id] = 20
                        value = base[tag_id]

                        cur.execute(
                            "INSERT INTO temperature_reading(tag_id, ts, value) VALUES (%s,%s,%s)",
                            (tag_id, now, value)
                        )
                c.commit()
                print(f" Inserted readings at {now.isoformat()}")
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\n Stopped simulation.")

if __name__ == "__main__":
    main()
