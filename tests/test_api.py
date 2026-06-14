import httpx


def test_upload():
    with open("testdata/sample_run.gpx", "rb") as f:
        response = httpx.post(
            "http://127.0.0.1:8000/api/activities/upload",
            files={"file": ("sample_run.gpx", f, "application/gpx+xml")},
        )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")


def test_list():
    response = httpx.get("http://127.0.0.1:8000/api/activities")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")


def test_detail(activity_id: int):
    response = httpx.get(f"http://127.0.0.1:8000/api/activities/{activity_id}")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Activity: {data['name']}")
    if data.get('stats'):
        print(f"  Distance: {data['stats']['distance_m']:.1f}m")
        print(f"  Duration: {data['stats']['duration_s']:.1f}s")
        print(f"  Elevation: +{data['stats']['elevation_gain']}m / -{data['stats']['elevation_loss']}m")
    if data.get('laps'):
        print(f"  Laps: {len(data['laps'])}")


if __name__ == "__main__":
    print("=== Upload GPX ===")
    test_upload()

    print("\n=== List Activities ===")
    test_list()

    print("\n=== Activity Detail ===")
    test_detail(1)
