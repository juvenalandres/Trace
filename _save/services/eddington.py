DISTANCE_UNIT_METERS = 1609.34


def compute_eddington(distances_meters: list[float]) -> int:
    distances_miles = [d / DISTANCE_UNIT_METERS for d in distances_meters]
    distances_miles.sort(reverse=True)

    e = 0
    for i, d in enumerate(distances_miles, start=1):
        if d >= i:
            e = i
        else:
            break
    return e


def eddington_progress(distances_meters: list[float], target: int) -> int:
    distances_miles = [d / DISTANCE_UNIT_METERS for d in distances_meters]
    return sum(1 for d in distances_miles if d >= target)
