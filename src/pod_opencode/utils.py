from datetime import datetime
from dateutil.parser import parse as parse_date_str
from typing import Optional


def java_date_to_iso(java_date) -> Optional[str]:
    """Convert Java Date to ISO 8601 date string (YYYY-MM-DD)."""
    if java_date is None:
        return None
    try:
        iso_str = str(java_date.toInstant())
        return iso_str[:10]
    except Exception:
        return None


def java_datetime_to_iso(java_date) -> Optional[str]:
    """Convert Java Date to ISO 8601 datetime string."""
    if java_date is None:
        return None
    try:
        return str(java_date.toInstant())
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
