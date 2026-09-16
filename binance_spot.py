"""Fetch full daily kline (candlestick) history for spot pairs from the Binance public API."""

import httpx

from utils import to_date

KLINES_URL = "https://api.binance.com/api/v3/klines"
MAX_LIMIT = 1000  # rows per request, Binance's hard cap


def fetch_klines(symbol: str, start_ms: int = 0) -> list[dict]:
    """Return every daily kline for `symbol` from `start_ms` (listing date by default) to now."""
    klines = []

    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(
                KLINES_URL,
                params={
                    "symbol": symbol,
                    "interval": "1d",
                    "startTime": start_ms,
                    "limit": MAX_LIMIT,
                },
            )
            resp.raise_for_status()
            rows = resp.json()
            klines.extend(
                {
                    "time": row[0],  # unix milliseconds, UTC — as Binance sends it
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
                for row in rows
            )
            if len(rows) < MAX_LIMIT:
                return klines
            start_ms = rows[-1][0] + 1


if __name__ == "__main__":
    btcusdt = fetch_klines("BTCUSDT")
    paxgusdt = fetch_klines("PAXGUSDT")
    print(f"BTCUSDT: {len(btcusdt)} days, {to_date(btcusdt[0]['time'])} -> {to_date(btcusdt[-1]['time'])}")
    print(f"PAXGUSDT: {len(paxgusdt)} days, {to_date(paxgusdt[0]['time'])} -> {to_date(paxgusdt[-1]['time'])}")
