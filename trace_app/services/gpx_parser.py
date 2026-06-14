import defusedxml.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

MAX_GPX_SIZE_MB = 50
MAX_GPX_DEPTH = 100


@dataclass
class TrackPoint:
    lat: float
    lng: float
    ele: float | None = None
    time: datetime | None = None
    hr: int | None = None
    cadence: int | None = None
    power: int | None = None
    temp: float | None = None


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def parse_gpx(content: str | bytes) -> list[TrackPoint]:
    if len(content) > MAX_GPX_SIZE_MB * 1024 * 1024:
        raise ValueError(f"GPX file exceeds maximum size of {MAX_GPX_SIZE_MB}MB")

    root = ET.fromstring(content) if isinstance(content, str) else ET.fromstring(content.decode())
    points: list[TrackPoint] = []

    for trkpt in root.iter():
        if _strip_ns(trkpt.tag) != "trkpt":
            continue

        lat = float(trkpt.get("lat"))
        lng = float(trkpt.get("lon"))

        ele: float | None = None
        time: datetime | None = None
        hr: int | None = None
        cadence: int | None = None
        power: int | None = None
        temp: float | None = None

        for child in trkpt:
            tag = _strip_ns(child.tag)
            if tag == "ele" and child.text:
                ele = float(child.text)
            elif tag == "time" and child.text:
                time = datetime.fromisoformat(child.text.replace("Z", "+00:00"))
            elif tag == "extensions":
                for ext_child in child:
                    ext_tag = _strip_ns(ext_child.tag)
                    if ext_tag == "TrackPointExtension":
                        for tpe_child in ext_child:
                            t = _strip_ns(tpe_child.tag)
                            if t == "hr" and tpe_child.text:
                                hr = int(tpe_child.text)
                            elif t == "cad" and tpe_child.text:
                                cadence = int(tpe_child.text)
                            elif t == "power" and tpe_child.text:
                                power = int(tpe_child.text)
                            elif t == "atemp" and tpe_child.text:
                                temp = float(tpe_child.text)
                    else:
                        _parse_generic_extensions(ext_child, _strip_ns)

        points.append(TrackPoint(
            lat=lat, lng=lng, ele=ele, time=time,
            hr=hr, cadence=cadence, power=power, temp=temp,
        ))
    return points


def _parse_generic_extensions(element, strip_ns):
    pass
