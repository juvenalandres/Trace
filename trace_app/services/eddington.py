DISTANCE_UNIT_METERS = 1609.34
DISTANCE_UNIT_KM = 1000.0


def get_unit_divisor(preferred_units: str) -> float:
    if preferred_units == "imperial":
        return DISTANCE_UNIT_METERS
    return DISTANCE_UNIT_KM


def get_unit_label(preferred_units: str) -> str:
    if preferred_units == "imperial":
        return "miles"
    return "km"


def compute_eddington(distances_meters: list[float], preferred_units: str = "metric") -> int:
    divisor = get_unit_divisor(preferred_units)
    distances = [d / divisor for d in distances_meters]
    distances.sort(reverse=True)

    e = 0
    for i, d in enumerate(distances, start=1):
        if d >= i:
            e = i
        else:
            break
    return e


def eddington_progress(distances_meters: list[float], target: int, preferred_units: str = "metric") -> int:
    divisor = get_unit_divisor(preferred_units)
    distances = [d / divisor for d in distances_meters]
    return sum(1 for d in distances if d >= target)
