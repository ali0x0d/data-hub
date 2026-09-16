"""Market data for bitcoin and gold."""

from pathlib import Path

from binance_spot import fetch_klines
from yahoo_finance import load_klines
from utils import to_date

DATA_DIR = Path(__file__).parent / "data"


def fetch_bitcoin() -> list[dict]:
    """BTC-USD from Yahoo (2014-09-17) until Binance lists BTCUSDT (2017-08-17), then Binance."""
    binance = fetch_klines("BTCUSDT")
    yahoo = load_klines(DATA_DIR / "btc_usd_daily.csv", until_ms=binance[0]["time"])
    return yahoo + binance


def fetch_gold() -> list[dict]:
    """GC=F gold futures from Yahoo (2000-08-30) until Binance lists PAXGUSDT (2020-08-28), then Binance."""
    binance = fetch_klines("PAXGUSDT")
    yahoo = load_klines(DATA_DIR / "gold_gc_f_daily.csv", until_ms=binance[0]["time"])
    return yahoo + binance


if __name__ == "__main__":
    bitcoin = fetch_bitcoin()
    gold = fetch_gold()
    print(f"bitcoin: {len(bitcoin)} bars, {to_date(bitcoin[0]['time'])} -> {to_date(bitcoin[-1]['time'])}")
    print(f"gold: {len(gold)} bars, {to_date(gold[0]['time'])} -> {to_date(gold[-1]['time'])}")
