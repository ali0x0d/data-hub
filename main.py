from contextlib import asynccontextmanager

from fastapi import FastAPI

from market_data import fetch_bitcoin, fetch_gold

data: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    data["bitcoin"] = fetch_bitcoin()
    data["gold"] = fetch_gold()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/bitcoin")
def bitcoin() -> list[dict]:
    return data["bitcoin"]


@app.get("/gold")
def gold() -> list[dict]:
    return data["gold"]
