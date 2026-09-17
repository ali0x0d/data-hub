"""Market data for bitcoin and gold."""

import asyncio
import logging
from pathlib import Path

import httpx

from binance_spot import fetch_klines
from yahoo_finance import load_klines
from utils import to_date

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
    return yahoo + binance


async def sync(btc: list[dict], xau: list[dict]) -> None:
    """Keep btc and xau up to date with Binance, polling every SYNC_INTERVAL seconds."""
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


if __name__ == "__main__":
    btc = asyncio.run(fetch_btc())
    xau = asyncio.run(fetch_xau())
    print(f"btc: {len(btc)} bars, {to_date(btc[0]['time'])} -> {to_date(btc[-1]['time'])}")
    print(f"xau: {len(xau)} bars, {to_date(xau[0]['time'])} -> {to_date(xau[-1]['time'])}")
