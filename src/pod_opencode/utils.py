from datetime import datetime
from dateutil.parser import parse as parse_date_str
from typing import Optional


def java_date_to_iso(java_date) -> Optional[str]:
    """Convert a Java date (java.util.Date or java.time.LocalDateTime) to
    ISO 8601 date string (YYYY-MM-DD)."""
    if java_date is None:
        return None
    try:
        iso_str = str(java_date.toInstant())
        return iso_str[:10]
    except Exception:
        pass
    try:
        # MPXJ 16 returns java.time temporals which have no toInstant().
        text = str(java_date)
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return text[:10]
        return None
    except Exception:
        return None


def java_datetime_to_iso(java_date) -> Optional[str]:
    """Convert a Java date to ISO 8601 datetime string."""
    if java_date is None:
        return None
    try:
        return str(java_date.toInstant())
    except Exception:
        pass
    try:
        return str(java_date)
    except Exception:
        return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse a date string and return a Python datetime. Returns None on parse failure."""
    try:
        return parse_date_str(date_str)
    except Exception:
        return None


def duration_to_str(duration) -> Optional[str]:
    """Convert MPXJ Duration object to human-readable string (e.g., '60d', '480h')."""
    if duration is None:
        return None
    try:
        return str(duration)
    except Exception:
        return None


def jstr(value) -> Optional[str]:
    """Coerce a JPype Java String (or any object) to a Python str.

    MPXJ returns java.lang.String objects which Pydantic v2 does not
    accept as str. None stays None, empty string stays empty string.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:
        return None


def get_task_field(task, field):
    """Safely get a task field, returning None if not found."""
    try:
        return task.get(field)
    except Exception:
        return None


def get_resource_field(resource, field):
    """Safely get a resource field, returning None if not found."""
    try:
        return resource.get(field)
    except Exception:
        return None


def jint(value: int):
    """Box a Python int as java.lang.Integer.

    Required because JPype does not auto-select the Integer overload of
    MPXJ lookup methods like getTaskByUniqueID(Integer).
    """
    import jpype

    return jpype.java.lang.Integer(value)


def next_ids(items):
    """Return (next_id, next_unique_id) as max+1 over a task/resource list.

    Projects loaded by a reader do not auto-assign IDs to newly added
    items, and MSPDIWriter sorts tasks by ID, so callers must assign IDs
    explicitly before writing.
    """
    ids = [int(i.getID()) for i in items if i.getID() is not None]
    uids = [int(i.getUniqueID()) for i in items if i.getUniqueID() is not None]
    return (max(ids or [0]) + 1, max(uids or [0]) + 1)


def to_java_datetime(dt):
    """Convert a Python datetime to java.time.LocalDateTime (MPXJ 16 API)."""
    import jpype

    return jpype.java.time.LocalDateTime.of(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
    )


def parse_duration(text):
    """Parse '5d', '40h', '2w' into an MPXJ Duration. Returns None if invalid."""
    import re

    m = re.match(r"^\s*([\d.]+)\s*([a-zA-Z%]+)\s*$", text or "")
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    from org.mpxj import Duration, TimeUnit

    units = {
        "m": TimeUnit.MINUTES,
        "h": TimeUnit.HOURS,
        "d": TimeUnit.DAYS,
        "w": TimeUnit.WEEKS,
        "mo": TimeUnit.MONTHS,
        "y": TimeUnit.YEARS,
        "%": TimeUnit.PERCENT,
    }
    unit = units.get(m.group(2).lower())
    if unit is None:
        return None
    return Duration.getInstance(value, unit)
