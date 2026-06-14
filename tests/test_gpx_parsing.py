import json
from pathlib import Path

from trace_app.services.activity_processor import process_activity
from trace_app.services.gpx_parser import parse_gpx


def test_gpx_parsing():
    gpx_path = Path("testdata/sample_run.gpx")
    content = gpx_path.read_text()

    points = parse_gpx(content)
    print(f"Parsed {len(points)} track points")

    for i, p in enumerate(points):
        print(f"  Point {i}: lat={p.lat}, lng={p.lng}, ele={p.ele}, "
              f"time={p.time}, hr={p.hr}, cad={p.cadence}, power={p.power}")

    print()
    result = process_activity(points)

    print("=== Computed Stats ===")
    print(f"  Distance: {result['distance_m']:.1f} m")
    print(f"  Duration: {result['duration_s']:.1f} s")
    print(f"  Moving time: {result['moving_time_s']:.1f} s")
    print(f"  Elevation gain: {result['elevation_gain']:.1f} m")
    print(f"  Elevation loss: {result['elevation_loss']:.1f} m")
    print(f"  Avg speed: {result['avg_speed']:.2f} m/s")
    print(f"  Max speed: {result['max_speed']:.2f} m/s")
    print(f"  Avg HR: {result['avg_hr']}")
    print(f"  Max HR: {result['max_hr']}")
    print(f"  Avg power: {result['avg_power']}")
    print(f"  Max power: {result['max_power']}")
    print(f"  Avg cadence: {result['avg_cadence']}")

    print()
    print("=== Polyline ===")
    print(f"  Length: {len(result['polyline'])} chars")

    print()
    print("=== Elevation Profile ===")
    profile = json.loads(result['elevation_profile'])
    print(f"  Points: {len(profile)}")

    print()
    print("=== Simplified Time Series ===")
    ts = json.loads(result['simplified_time_series'])
    print(f"  Points: {len(ts)}")
    for pt in ts[:3]:
        print(f"    d={pt['d']}m, ele={pt['ele']}m, spd={pt['spd']}m/s, hr={pt['hr']}")

    print()
    print("=== Bounds ===")
    print(f"  Lat: {result['min_lat']:.4f} to {result['max_lat']:.4f}")
    print(f"  Lng: {result['min_lng']:.4f} to {result['max_lng']:.4f}")

    print()
    print("=== Auto-laps ===")
    print(f"  Generated: {len(result['laps'])} laps")
    for lap in result['laps']:
        print(f"    Lap {lap['lap_index']}: {lap['distance_m']:.1f}m, "
              f"{lap['duration_s']:.1f}s, avg_hr={lap['avg_hr']}")


if __name__ == "__main__":
    test_gpx_parsing()
