"""Pure data-cleaning helpers for the 'messy' cases in the brief.

1. Ported-out subscribers still marked active  -> reconcile_status
2. Duplicate complaints (app + call centre)     -> find_duplicate
3. Data usage in MB and GB mixed                -> normalize_usage_to_mb / parse_usage_string
"""
import re
from datetime import date, datetime, timedelta

UNIT_TO_MB = {"kb": 1 / 1024, "mb": 1.0, "gb": 1024.0, "tb": 1024.0**2}
_USAGE_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)\s*$")
DUPLICATE_WINDOW = timedelta(hours=24)


def normalize_usage_to_mb(value: float, unit: str) -> float:
    factor = UNIT_TO_MB.get((unit or "").strip().lower())
    if factor is None:
        raise ValueError(f"Unsupported data unit: {unit!r} (use MB or GB)")
    if value < 0:
        raise ValueError("Usage cannot be negative")
    return round(value * factor, 2)


def parse_usage_string(raw: str) -> tuple[float, str]:
    """'1.5 GB' / '800mb' -> (1.5, 'GB') / (800.0, 'MB')."""
    match = _USAGE_RE.match(raw or "")
    if not match:
        raise ValueError(f"Cannot parse usage value: {raw!r}")
    return float(match.group(1)), match.group(2).upper()


def reconcile_status(status: str, ported_out_at: date | None, today: date | None = None) -> tuple[str, bool]:
    """A subscriber with a ported-out date in the past cannot still be 'active'.
    Returns (effective_status, was_corrected)."""
    today = today or date.today()
    if ported_out_at is not None and ported_out_at <= today and status != "ported_out":
        return "ported_out", True
    return status, False


def find_duplicate(candidates, created_at: datetime, window: timedelta = DUPLICATE_WINDOW):
    """Return the earliest still-open complaint for the same subscriber+category that
    was logged within `window` before `created_at` (the same issue raised twice)."""
    matches = [c for c in candidates if timedelta(0) <= created_at - c.created_at <= window]
    return min(matches, key=lambda c: (c.created_at, c.id)) if matches else None
