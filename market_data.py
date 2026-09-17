"""Market data for bitcoin and gold."""

import asyncio
import logging
from pathlib import Path

import httpx

from binance_spot import fetch_klines
from yahoo_finance import load_klines
from utils import DAY_MS, fill_missing_days, to_date

DATA_DIR = Path(__file__).parent / "data"
SYNC_INTERVAL = 5  # seconds

logger = logging.getLogger(__name__)


async def fetch_btc() -> list[dict]:
    """BTC-USD from Yahoo (2014-09-17) until Binance lists BTCUSDT (2017-08-17), then Binance."""
    binance = await fetch_klines("BTCUSDT")
    yahoo = load_klines(DATA_DIR / "btc_usd_daily.csv", until_ms=binance[0]["time"])
    return yahoo + binance


async def fetch_xau() -> list[dict]:
    """GC=F gold futures from Yahoo (2000-08-30) until Binance lists PAXGUSDT (2020-08-28), then Binance."""
    binance = await fetch_klines("PAXGUSDT")
    yahoo = load_klines(DATA_DIR / "gold_gc_f_daily.csv", until_ms=binance[0]["time"])
    return fill_missing_days(yahoo + binance)


def compute_btcxau(btc: list[dict], xau: list[dict]) -> list[dict]:
    """Bitcoin priced in gold, bar by bar; both series must be gapless and end on the same day.
    Open and close are exact; high and low are the extremes of the four ratios, since the true
    intraday range can't be known from daily bars."""
    btcxau = []
    for b, x in zip(btc, xau[-len(btc):]):
        ratio = {k: b[k] / x[k] for k in ("open", "high", "low", "close")}
        btcxau.append(
            {
                "time": b["time"],
                "open": ratio["open"],
                "high": max(ratio.values()),
                "low": min(ratio.values()),
                "close": ratio["close"],
            }
        )
    return btcxau


async def sync(btc: list[dict], xau: list[dict], btcxau: list[dict]) -> None:
    """Keep btc, xau and their ratio up to date with Binance, polling every SYNC_INTERVAL seconds."""
    while True:
        await asyncio.sleep(SYNC_INTERVAL)
        try:
            fresh_btc, fresh_xau = await asyncio.gather(
                fetch_klines("BTCUSDT", start_ms=btc[-1]["time"]),
                fetch_klines("PAXGUSDT", start_ms=xau[-1]["time"]),
            )
        except httpx.HTTPError as e:
            logger.warning("sync failed, retrying in %ss: %s", SYNC_INTERVAL, e)
            continue
        if fresh_btc:
            btc[-1:] = fresh_btc
        if fresh_xau:
            xau[-1:] = fresh_xau
        if xau[-1]["time"] == btc[-1]["time"]:  # PAXG's new day can show up a poll after BTCUSDT's
            k = (btc[-1]["time"] - btcxau[-1]["time"]) // DAY_MS + 1  # 1, or 2 right after midnight UTC
            btcxau[-1:] = compute_btcxau(btc[-k:], xau[-k:])


if __name__ == "__main__":
    btc = asyncio.run(fetch_btc())
    xau = asyncio.run(fetch_xau())
    print(f"btc: {len(btc)} bars, {to_date(btc[0]['time'])} -> {to_date(btc[-1]['time'])}")
    print(f"xau: {len(xau)} bars, {to_date(xau[0]['time'])} -> {to_date(xau[-1]['time'])}")
