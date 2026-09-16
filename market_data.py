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


async def fetch_bitcoin() -> list[dict]:
    """BTC-USD from Yahoo (2014-09-17) until Binance lists BTCUSDT (2017-08-17), then Binance."""
    binance = await fetch_klines("BTCUSDT")
    yahoo = load_klines(DATA_DIR / "btc_usd_daily.csv", until_ms=binance[0]["time"])
    return yahoo + binance


async def fetch_gold() -> list[dict]:
    """GC=F gold futures from Yahoo (2000-08-30) until Binance lists PAXGUSDT (2020-08-28), then Binance."""
    binance = await fetch_klines("PAXGUSDT")
    yahoo = load_klines(DATA_DIR / "gold_gc_f_daily.csv", until_ms=binance[0]["time"])
    return yahoo + binance


async def sync(bitcoin: list[dict], gold: list[dict]) -> None:
    """Keep bitcoin and gold up to date with Binance, polling every SYNC_INTERVAL seconds."""
    while True:
        await asyncio.sleep(SYNC_INTERVAL)
        try:
            fresh_bitcoin, fresh_gold = await asyncio.gather(
                fetch_klines("BTCUSDT", start_ms=bitcoin[-1]["time"]),
                fetch_klines("PAXGUSDT", start_ms=gold[-1]["time"]),
            )
        except httpx.HTTPError as e:
            logger.warning("sync failed, retrying in %ss: %s", SYNC_INTERVAL, e)
            continue
        if fresh_bitcoin:
            bitcoin[-1:] = fresh_bitcoin
        if fresh_gold:
            gold[-1:] = fresh_gold


if __name__ == "__main__":
    bitcoin = asyncio.run(fetch_bitcoin())
    gold = asyncio.run(fetch_gold())
    print(f"bitcoin: {len(bitcoin)} bars, {to_date(bitcoin[0]['time'])} -> {to_date(bitcoin[-1]['time'])}")
    print(f"gold: {len(gold)} bars, {to_date(gold[0]['time'])} -> {to_date(gold[-1]['time'])}")
