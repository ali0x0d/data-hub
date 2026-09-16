"""Load daily OHLCV history downloaded from Yahoo Finance (the CSVs in data/)."""

import csv
from datetime import UTC, datetime
from pathlib import Path


def load_klines(path: Path | str, until_ms: int) -> list[dict]:
    """Return the bars in `path` dated before `until_ms`, in the same shape as Binance klines."""
    klines = []

    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            # unix milliseconds at 00:00 UTC of the Yahoo trading date
            time_ms = int(datetime.fromisoformat(row["Date"]).replace(tzinfo=UTC).timestamp() * 1000)
            if time_ms < until_ms:
                klines.append(
                    {
                        "time": time_ms,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": float(row["Volume"]),
                    }
                )

    return klines
