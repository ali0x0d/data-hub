"""Small helpers shared across the project."""

from datetime import UTC, date, datetime

DAY_MS = 86_400_000


def to_date(ms: int) -> date:
    """Calendar date (UTC) of a millisecond timestamp."""
    return datetime.fromtimestamp(ms / 1000, UTC).date()


def fill_missing_days(klines: list[dict]) -> list[dict]:
    """Add a candle for every missing day: previous close held flat, zero volume."""
    filled = []
    for bar in klines:
        while filled and filled[-1]["time"] + DAY_MS < bar["time"]:
            prev = filled[-1]
            filled.append(
                {
                    "time": prev["time"] + DAY_MS,
                    "open": prev["close"],
                    "high": prev["close"],
                    "low": prev["close"],
                    "close": prev["close"],
                    "volume": 0.0,
                }
            )
        filled.append(bar)
    return filled
