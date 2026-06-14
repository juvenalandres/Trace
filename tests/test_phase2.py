import asyncio
import json

from httpx import AsyncClient, ASGITransport

from trace_app.main import app


async def test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register
        r = await client.post("/api/auth/register", json={"email": "test@example.com", "password": "testpass123"})
        print(f"Register: {r.status_code}")
        tokens = r.json()
        access = tokens["access_token"]

        # Login
        r = await client.post("/api/auth/login", json={"email": "test@example.com", "password": "testpass123"})
        print(f"Login: {r.status_code}")

        # Refresh
        r = await client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        print(f"Refresh: {r.status_code}")

        headers = {"Authorization": f"Bearer {access}"}

        # Get me
        r = await client.get("/api/me", headers=headers)
        print(f"Me: {r.status_code} email={r.json()['email']}")

        # Update me
        r = await client.put("/api/me?name=TestRunner&preferred_units=metric", headers=headers)
        print(f"Update me: {r.status_code} name={r.json()['name']}")

        # Create zone
        r = await client.post("/api/zones", headers=headers, json={
            "zone_type": "hr",
            "zone_1_max": 120,
            "zone_2_min": 120, "zone_2_max": 140,
            "zone_3_min": 140, "zone_3_max": 160,
            "zone_4_min": 160, "zone_4_max": 175,
            "zone_5_min": 175,
        })
        print(f"Create zone: {r.status_code}")

        # List zones
        r = await client.get("/api/zones", headers=headers)
        print(f"List zones: {r.status_code} count={len(r.json())}")

        # Upload GPX
        with open("testdata/sample_run.gpx", "rb") as f:
            r = await client.post(
                "/api/activities/upload",
                headers=headers,
                files={"file": ("sample_run.gpx", f, "application/gpx+xml")},
            )
        print(f"Upload: {r.status_code}")
        activity = r.json()
        activity_id = activity["id"]

        # List activities
        r = await client.get("/api/activities", headers=headers)
        print(f"List: {r.status_code} total={r.json()['total']}")

        # Detail
        r = await client.get(f"/api/activities/{activity_id}", headers=headers)
        print(f"Detail: {r.status_code} dist={r.json()['stats']['distance_m']}m")

        # Update activity
        r = await client.put(
            f"/api/activities/{activity_id}",
            headers=headers,
            json={"name": "Morning Run", "sport_type": "run"},
        )
        print(f"Update: {r.status_code} name={r.json()['name']} sport={r.json()['sport_type']}")

        # Create gear
        r = await client.post("/api/gear", headers=headers, json={
            "name": "Daily Trainers",
            "gear_type": "shoes",
            "brand": "Nike",
            "model": "Pegasus 41",
            "maintenance_interval_km": 800,
        })
        print(f"Create gear: {r.status_code}")
        gear_id = r.json()["id"]

        # List gear
        r = await client.get("/api/gear", headers=headers)
        print(f"List gear: {r.status_code} count={len(r.json())}")

        # Dashboard
        r = await client.get("/api/stats/dashboard", headers=headers)
        print(f"Dashboard: {r.status_code} all_time_dist={r.json()['all_time']['distance_m']}")

        # Eddington
        r = await client.get("/api/stats/eddington", headers=headers)
        print(f"Eddington: {r.status_code} e={r.json()['eddington_number']}")

        # PRs
        r = await client.get("/api/stats/personal-records", headers=headers)
        print(f"PRs: {r.status_code}")

        print("\nAll endpoints working!")


asyncio.run(test())
