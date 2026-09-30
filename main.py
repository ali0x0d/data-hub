import asyncio
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from market_data import compute_btcxau, fetch_btc, fetch_xau, sync

API_TOKEN = os.environ["API_TOKEN"]
ALLOWED_ORIGINS = [
    origin.strip() for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",") if origin.strip()
]
DEV_MODE = os.environ.get("FASTAPI_ENV") == "development"  # set by `fastapi dev`, not by `fastapi run`

bearer = HTTPBearer()

data: dict[str, list[dict]] = {}


def require_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> None:
    if not secrets.compare_digest(credentials.credentials, API_TOKEN):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    data["btc"], data["xau"] = await asyncio.gather(fetch_btc(), fetch_xau())
    data["btcxau"] = compute_btcxau(data["btc"], data["xau"])
    task = asyncio.create_task(sync(data["btc"], data["xau"], data["btcxau"]))
    yield
    task.cancel()


app = FastAPI(
    lifespan=lifespan,
    dependencies=[Depends(require_token)],
    openapi_url="/openapi.json" if DEV_MODE else None,  # None also removes /docs and /redoc
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_headers=["Authorization"],
)


@app.get("/btc")
def btc() -> list[dict]:
    return data["btc"]


@app.get("/xau")
def xau() -> list[dict]:
    return data["xau"]


@app.get("/btcxau")
def btcxau() -> list[dict]:
    return data["btcxau"]
