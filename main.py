import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from market_data import fetch_bitcoin, fetch_gold, sync

data: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    data["bitcoin"], data["gold"] = await asyncio.gather(fetch_bitcoin(), fetch_gold())
    task = asyncio.create_task(sync(data["bitcoin"], data["gold"]))
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/bitcoin")
def bitcoin() -> list[dict]:
    return data["bitcoin"]


@app.get("/gold")
def gold() -> list[dict]:
    return data["gold"]
