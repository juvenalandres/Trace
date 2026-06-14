"""
Stress test for Trace API.
Uses FastAPI TestClient in-process (no network overhead).
Spwans a fresh Python process per database size to ensure clean imports.
"""
import json
import os
import sys
import time
import sqlite3
import subprocess
import random
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).parent
TEST_DIR = PROJECT_ROOT / "stress_test_db"

SPORT_TYPES = ["run", "ride", "swim", "hike", "walk"]
SPORT_WEIGHTS = [0.35, 0.25, 0.10, 0.15, 0.15]


def weighted_choice(items, weights):
    r = random.random()
    cumulative = 0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


def create_database(db_path: str, num_activities: int):
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255),
            name VARCHAR(255),
            preferred_units VARCHAR(20) DEFAULT 'metric',
            weight_kg FLOAT,
            ftp_watts INTEGER,
            max_hr INTEGER,
            resting_hr INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE activities (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name VARCHAR(255) NOT NULL,
            sport_type VARCHAR(50) NOT NULL,
            start_time DATETIME NOT NULL,
            timezone VARCHAR(50),
            source VARCHAR(50) DEFAULT 'manual',
            raw_file_path VARCHAR(500),
            gear_id INTEGER,
            notes TEXT,
            rpe INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE activity_stats (
            id INTEGER PRIMARY KEY,
            activity_id INTEGER NOT NULL REFERENCES activities(id),
            distance_m FLOAT,
            duration_s FLOAT,
            moving_time_s FLOAT,
            elevation_gain FLOAT,
            elevation_loss FLOAT,
            avg_speed FLOAT,
            max_speed FLOAT,
            avg_hr FLOAT,
            max_hr INTEGER,
            avg_power FLOAT,
            max_power INTEGER,
            normalized_power FLOAT,
            avg_cadence FLOAT,
            calories INTEGER,
            avg_temp FLOAT,
            polyline TEXT,
            simplified_time_series TEXT,
            elevation_profile TEXT,
            min_lat FLOAT,
            max_lat FLOAT,
            min_lng FLOAT,
            max_lng FLOAT,
            training_load FLOAT
        );

        CREATE TABLE IF NOT EXISTS daily_training_load (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            date DATE NOT NULL,
            total_load FLOAT DEFAULT 0,
            ctl FLOAT DEFAULT 0,
            atl FLOAT DEFAULT 0,
            tsb FLOAT DEFAULT 0,
            acwr FLOAT DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS ix_activities_user_id ON activities(user_id);
        CREATE INDEX IF NOT EXISTS ix_activities_start_time ON activities(start_time);
        CREATE INDEX IF NOT EXISTS ix_activities_user_sport ON activities(user_id, sport_type);
        CREATE INDEX IF NOT EXISTS ix_activities_user_date ON activities(user_id, start_time);
        CREATE INDEX IF NOT EXISTS ix_activity_stats_activity_id ON activity_stats(activity_id);
        CREATE INDEX IF NOT EXISTS ix_daily_training_load_user_id_date ON daily_training_load(user_id, date);
    """)

    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    pw_hash = pwd_context.hash("test123")

    conn.execute(
        "INSERT INTO users (id, email, password_hash, name, preferred_units, weight_kg, ftp_watts, max_hr, resting_hr) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, "test@test.com", pw_hash, "Test User", "km", 75, 250, 190, 45)
    )

    now = datetime.utcnow()
    t0 = time.time()

    chunk_size = 1000
    for chunk_start in range(0, num_activities, chunk_size):
        chunk_end = min(chunk_start + chunk_size, num_activities)
        activities = []
        stats = []

        for i in range(chunk_start, chunk_end):
            aid = i + 1
            sport = weighted_choice(SPORT_TYPES, SPORT_WEIGHTS)
            days_ago = random.randint(0, 730)
            start = now - timedelta(
                days=days_ago,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            if sport == "run":
                distance = random.uniform(3000, 42000)
                duration = distance / random.uniform(2.5, 5.0)
                elevation = random.uniform(10, 600)
            elif sport == "ride":
                distance = random.uniform(10000, 200000)
                duration = distance / random.uniform(5.0, 10.0)
                elevation = random.uniform(50, 2000)
            elif sport == "swim":
                distance = random.uniform(500, 5000)
                duration = distance / random.uniform(0.8, 1.5)
                elevation = 0
            elif sport == "hike":
                distance = random.uniform(3000, 30000)
                duration = distance / random.uniform(1.0, 2.0)
                elevation = random.uniform(50, 1500)
            else:
                distance = random.uniform(1000, 15000)
                duration = distance / random.uniform(1.0, 2.5)
                elevation = random.uniform(5, 200)

            avg_hr = random.randint(110, 170)
            max_hr = avg_hr + random.randint(10, 40)
            avg_power = random.randint(80, 300) if sport == "ride" else random.randint(100, 250)
            max_power = avg_power + random.randint(50, 200)
            avg_cadence = random.randint(65, 100)
            calories = random.randint(100, 2000)
            training_load = random.uniform(50, 500)
            start_str = start.strftime("%Y-%m-%dT%H:%M:%S")

            activities.append((
                aid, 1, f"{sport.title()} Activity {aid}", sport,
                start_str, None, "manual", None, None, None, None,
                start_str, start_str
            ))

            stats.append((
                aid, aid, distance, duration, duration * random.uniform(0.92, 1.0),
                elevation, elevation * random.uniform(0.05, 0.2),
                distance / duration, distance / duration * random.uniform(1.2, 1.6),
                avg_hr, max_hr, avg_power, max_power,
                avg_power * random.uniform(0.95, 1.0),
                avg_cadence, calories, None, None, None, None,
                None, None, None, None, training_load
            ))

        conn.executemany(
            "INSERT INTO activities (id, user_id, name, sport_type, start_time, timezone, source, raw_file_path, gear_id, notes, rpe, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            activities
        )
        conn.executemany(
            "INSERT INTO activity_stats (id, activity_id, distance_m, duration_s, moving_time_s, elevation_gain, elevation_loss, avg_speed, max_speed, avg_hr, max_hr, avg_power, max_power, normalized_power, avg_cadence, calories, avg_temp, polyline, simplified_time_series, elevation_profile, min_lat, max_lat, min_lng, max_lng, training_load) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            stats
        )
        conn.commit()

    elapsed = time.time() - t0
    size_mb = os.path.getsize(db_path) / 1024 / 1024
    conn.close()
    print(f"  DB created ({num_activities} activities, {elapsed:.1f}s, {size_mb:.1f} MB)")


def run_single_test(num: int) -> dict:
    """Run test for one database size. Called in a fresh process."""
    db_path = TEST_DIR / f"test_{num}.db"
    create_database(str(db_path), num)

    # Set env BEFORE importing trace_app
    os.environ["TRACE_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    os.environ["TRACE_JWT_SECRET"] = "stress-test-secret-key"

    from trace_app.main import app
    from trace_app.services.auth import create_access_token
    from fastapi.testclient import TestClient

    token = create_access_token(1)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}

    endpoints = [
        ("GET", "/api/stats/dashboard", "Dashboard"),
        ("GET", "/api/activities?page=1&page_size=20", "Activities (p1, sz20)"),
        ("GET", "/api/activities?page=1&page_size=100", "Activities (p1, sz100)"),
        ("GET", "/api/activities?page=1&page_size=1000", "Activities (p1, sz1000)"),
        ("GET", "/api/stats/volume", "Volume Stats"),
        ("GET", "/api/stats/personal-records", "Personal Records"),
        ("GET", "/api/stats/heatmap", "Heatmap"),
        ("GET", "/api/stats/eddington", "Eddington"),
        ("GET", "/api/training/insights", "Training Insights"),
    ]

    print("  --- Cold start (first request) ---")
    cold = {}
    for method, path, label in endpoints:
        t0 = time.perf_counter()
        resp = client.request(method, path, headers=headers)
        elapsed = (time.perf_counter() - t0) * 1000
        cold[label] = elapsed
        status = "OK" if resp.status_code == 200 else f"E{resp.status_code}"
        print(f"  {status:4s} {elapsed:>8.0f}ms  {label}")

    print("  --- Warm (steady state) ---")
    warm = {}
    for method, path, label in endpoints:
        t0 = time.perf_counter()
        resp = client.request(method, path, headers=headers)
        elapsed = (time.perf_counter() - t0) * 1000
        warm[label] = elapsed
        status = "OK" if resp.status_code == 200 else f"E{resp.status_code}"
        print(f"  {status:4s} {elapsed:>8.0f}ms  {label}")

    # Print as JSON for parent process to parse
    result = {"num": num, "cold": cold, "warm": warm}
    print(f"---RESULT:{json.dumps(result)}---")
    return result


if __name__ == "__main__":
    TEST_DIR.mkdir(exist_ok=True)

    # If called with an arg (from subprocess), run one test
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        run_single_test(int(sys.argv[1]))
        sys.exit(0)

    # Otherwise, orchestrate: run each size in a fresh subprocess
    all_results = {}
    for num in [100, 1000, 10000]:
        print(f"\n{'='*65}")
        print(f"  TEST: {num} activities")
        print(f"{'='*65}")
        proc = subprocess.run(
            [sys.executable, __file__, str(num)],
            capture_output=True, text=True, timeout=120,
            cwd=str(PROJECT_ROOT),
        )
        if proc.returncode != 0:
            print(f"  FAILED (exit {proc.returncode})")
            print(proc.stderr)
            continue
        # Find and parse the result JSON
        for line in proc.stdout.split("\n"):
            if line.startswith("---RESULT:"):
                raw = line[len("---RESULT:"):]
                # Strip any trailing markers
                if raw.endswith("---"):
                    raw = raw[:-3]
                all_results[num] = json.loads(raw)
                print(proc.stdout)

    print(f"\n{'='*65}")
    print("  COLD START (first request after import)")
    print(f"{'='*65}")
    labels = list(next(iter(all_results.values()))["cold"].keys())
    print(f"{'Endpoint':<28s} {'100':>8s} {'1000':>8s} {'10000':>8s}")
    print("-" * 55)
    for label in labels:
        row = f"{label:<28s}"
        for num in [100, 1000, 10000]:
            row += f" {all_results[num]['cold'].get(label, 0):>7.0f}ms"
        print(row)

    print()
    print(f"{'='*65}")
    print("  STEADY STATE (warmed up)")
    print(f"{'='*65}")
    print(f"{'Endpoint':<28s} {'100':>8s} {'1000':>8s} {'10000':>8s}")
    print("-" * 55)
    for label in labels:
        row = f"{label:<28s}"
        for num in [100, 1000, 10000]:
            row += f" {all_results[num]['warm'].get(label, 0):>7.0f}ms"
        print(row)

    # Cleanup
    print()
    for num in [100, 1000, 10000]:
        db_path = TEST_DIR / f"test_{num}.db"
        if db_path.exists():
            db_path.unlink()
            print(f"  Cleaned {db_path.name}")
