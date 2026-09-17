import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from market_data import compute_btcxau, fetch_btc, fetch_xau, sync

data: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    data["btc"], data["xau"] = await asyncio.gather(fetch_btc(), fetch_xau())
    data["btcxau"] = compute_btcxau(data["btc"], data["xau"])
    task = asyncio.create_task(sync(data["btc"], data["xau"], data["btcxau"]))
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/btc")
def btc() -> list[dict]:
    return data["btc"]


@app.get("/xau")
def xau() -> list[dict]:
    return data["xau"]


@app.get("/btcxau")
def btcxau() -> list[dict]:
    return data["btcxau"]
