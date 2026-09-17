import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from market_data import fetch_btc, fetch_xau, sync

data: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    data["btc"], data["xau"] = await asyncio.gather(fetch_btc(), fetch_xau())
    task = asyncio.create_task(sync(data["btc"], data["xau"]))
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/btc")
def btc() -> list[dict]:
    return data["btc"]


@app.get("/xau")
def xau() -> list[dict]:
    return data["xau"]
