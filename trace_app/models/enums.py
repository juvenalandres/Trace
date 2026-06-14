import enum


class SportType(str, enum.Enum):
    RUN = "run"
    RIDE = "ride"
    SWIM = "swim"
    HIKE = "hike"
    WALK = "walk"
    OTHER = "other"


class Source(str, enum.Enum):
    MANUAL = "manual"
    GPX = "gpx"
    FIT = "fit"
    GARMIN = "garmin"


class GearType(str, enum.Enum):
    BIKE = "bike"
    SHOES = "shoes"
    OTHER = "other"


class SyncProvider(str, enum.Enum):
    GARMIN = "garmin"
    FITBIT = "fitbit"
    WAHOO = "wahoo"
    POLAR = "polar"


class ZoneType(str, enum.Enum):
    HR = "hr"
    POWER = "power"


class TargetType(str, enum.Enum):
    DISTANCE = "distance"
    DURATION = "duration"
    PACE = "pace"
    HR_ZONE = "hr_zone"
    POWER_ZONE = "power_zone"
    FREE = "free"


class SessionStatus(str, enum.Enum):
    PLANNED = "planned"
    COMPLETED = "completed"
    SKIPPED = "skipped"
