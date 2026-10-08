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


def units_to_java(fraction):
    """Convert a user fraction (1.0 = full time) to MPXJ percent-points.

    MPXJ 16 reads and writes units as percent-points (100.0 = 100%),
    which is also what MSPDI stores (1 = 100%). The CLI speaks fractions,
    so scale here at the single boundary point.
    """
    return float(fraction) * 100.0


def units_from_java(value):
    """Convert MPXJ percent-points back to a user fraction. None stays None."""
    if value is None:
        return None
    return float(value) / 100.0


def set_resource_max_units(resource, fraction):
    """Set overall availability (max units) from a fraction (1.0 = full).

    MPXJ 16 removed setMaxUnits; availability is stored per date range in
    percent-points. A single wide range means "always at this level".
    """
    from org.mpxj import Availability

    table = resource.getAvailability()
    table.clear()
    table.add(
        Availability(
            to_java_datetime(parse_date("2000-01-01")),
            to_java_datetime(parse_date("2100-01-01")),
            units_to_java(fraction),
        )
    )


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


def suggest_name(value, refs, project, kind="task"):
    """Build a 'did you mean?' hint for an unresolved name or ref."""
    import difflib

    candidates = [k for k in refs if isinstance(k, str)]
    if kind == "task":
        candidates += [
            jstr(t.getName()) for t in project.getTasks() if jstr(t.getName())
        ]
    else:
        candidates += [
            jstr(r.getName()) for r in project.getResources() if jstr(r.getName())
        ]
    close = difflib.get_close_matches(str(value), candidates, n=2, cutoff=0.6)
    return f" (did you mean: {', '.join(close)})?" if close else ""


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


class ValidationError(ValueError):
    """Raised when user-supplied option values are invalid."""


def check_effective_order(cur_start, cur_finish, start_dt, finish_dt):
    """Ensure the merged new/existing dates stay consistent.

    cur_start/cur_finish are the task's current Java temporals (or None);
    start_dt/finish_dt are new Python datetimes (or None). Raises
    ValidationError when the effective finish precedes the effective start.
    """
    eff_start = to_java_datetime(start_dt) if start_dt is not None else cur_start
    eff_finish = to_java_datetime(finish_dt) if finish_dt is not None else cur_finish
    if eff_start is None or eff_finish is None:
        return
    try:
        bad = bool(eff_finish.isBefore(eff_start))
    except Exception:
        bad = str(eff_finish) < str(eff_start)
    if bad:
        raise ValidationError(
            "effective finish date is before effective start date; "
            "pass --finish explicitly"
        )


def validate_task_inputs(start=None, finish=None, duration=None, percent_complete=None):
    """Validate task options. Returns (start_dt, finish_dt, duration_obj).

    Raises ValidationError describing the first problem found.
    """
    start_dt = parse_date(start) if start else None
    if start and start_dt is None:
        raise ValidationError(f"Invalid start date: {start!r} (use YYYY-MM-DD)")
    finish_dt = parse_date(finish) if finish else None
    if finish and finish_dt is None:
        raise ValidationError(f"Invalid finish date: {finish!r} (use YYYY-MM-DD)")
    dur = parse_duration(duration) if duration else None
    if duration and dur is None:
        raise ValidationError(
            f"Invalid duration: {duration!r} (use e.g. '5d', '40h', '2w')"
        )
    if percent_complete is not None and not 0 <= percent_complete <= 100:
        raise ValidationError("percent-complete must be between 0 and 100")
    if start_dt and finish_dt and finish_dt < start_dt:
        raise ValidationError("finish date is before start date")
    return start_dt, finish_dt, dur
