"""Small helpers shared across the project."""

from datetime import UTC, date, datetime


def to_date(ms: int) -> date:
    """Calendar date (UTC) of a millisecond timestamp."""
    return datetime.fromtimestamp(ms / 1000, UTC).date()
