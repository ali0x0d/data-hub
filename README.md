# data-hub

A small FastAPI service that serves daily OHLC history for bitcoin, gold, and bitcoin priced in gold.

Each series is stitched together from two sources: a Yahoo Finance CSV for the years before the pair
existed on Binance, and the Binance public API from its listing date onward. The whole history is loaded
into memory at startup and the last bar is kept fresh by polling Binance every 5 seconds.

## Endpoints

All endpoints require a bearer token and return a JSON array of daily bars, oldest first.

| Endpoint  | Series                    | Starts at  | Sources                                          |
| --------- | ------------------------- | ---------- | ------------------------------------------------ |
| `/btc`    | Bitcoin in US dollars     | 2014-09-17 | Yahoo `BTC-USD`, then Binance `BTCUSDT` (2017-08-17)  |
| `/xau`    | Gold in US dollars        | 2000-08-30 | Yahoo `GC=F`, then Binance `PAXGUSDT` (2020-08-28)    |
| `/btcxau` | Bitcoin priced in gold    | 2014-09-17 | Computed from `/btc` and `/xau`                       |

A bar looks like this:

```json
{
  "time": 1410912000000,
  "open": 465.864014,
  "high": 468.174011,
  "low": 452.421997,
  "close": 457.334015,
  "volume": 21056800.0
}
```

`time` is unix milliseconds at 00:00 UTC of the trading day, exactly as Binance sends it. `/btcxau` bars
have no `volume` field.

### How the series are built

- **`/btc` is served exactly as its sources report it.** Nothing is rounded, adjusted or filled in, and
  bitcoin trades every day of the year, so no bar is ever missing.
- **`/xau` is gap filled.** Gold does not trade on weekends and holidays, so `GC=F` has gaps that would
  misalign it with bitcoin. Every missing day gets a candle holding the previous close flat, with zero
  volume. These filled days are synthetic, not source data.
- **`/btcxau` divides bar by bar.** Open and close are exact ratios. High and low are the extremes of the
  four possible ratios, because the true intraday range of the ratio cannot be recovered from daily bars.
- **The Yahoo and Binance halves do not agree perfectly** around the splice. Yahoo's `GC=F` is a futures
  contract and Binance's `PAXGUSDT` is a spot token, and the two dollar quotes for bitcoin come from
  different venues. Expect a small step at the boundary.

## Running locally

Install [uv](https://docs.astral.sh/uv/#installation) if you do not have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`uv sync` creates the virtualenv and downloads a Python 3.12 if the machine has none:

```bash
uv sync
cp .env.example .env
```

Put a token in `.env`; anything unguessable works, for example `openssl rand -hex 32`:

```
API_TOKEN=your-token-here
```

Then start the dev server:

```bash
uv run --env-file .env fastapi dev main.py
```

It listens on `http://127.0.0.1:8000` and takes a few seconds to come up while it pulls the full
Binance history.

```bash
curl -H "Authorization: Bearer your-token-here" http://127.0.0.1:8000/btcxau
```

Interactive docs are at `/docs` and `/redoc`. They are served only under `fastapi dev`; `fastapi run`
turns off the OpenAPI schema and both doc pages.

Each data module also runs on its own and prints what it fetched, which is handy for checking a source
without starting the API:

```bash
uv run python binance_spot.py
uv run python market_data.py
```

## Running with Docker

Needs [Docker Engine](https://docs.docker.com/engine/install/).

Build it yourself:

```bash
docker build -t data-hub .
docker run --rm -p 8000:8000 --env-file .env data-hub
```

Or run the image the workflow already published — `main` is the current deploy, and every build is also
tagged `sha-<short-sha>`:

```bash
docker run --rm -p 8000:8000 --env-file .env ghcr.io/ali0x0d/data-hub:main
```

GHCR packages are private by default, so unless the package is public, pulling it needs a personal access
token. It has to be a *classic* token — the container registry does not accept fine-grained ones. Create
one under **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new
token**, or straight from <https://github.com/settings/tokens/new?scopes=read:packages>, and tick only
the `read:packages` scope:

```bash
echo <personal-access-token> | docker login ghcr.io -u ali0x0d --password-stdin
```

## Deployment

Pushing to `main` triggers `.github/workflows/build-and-deploy.yml`, which builds the image, pushes it to
GHCR as `ghcr.io/ali0x0d/data-hub:main` (plus a `sha-<short-sha>` tag), then copies `compose.yaml` to the
server over SSH and runs `docker compose pull && docker compose up -d`.

The container publishes port 8000 on `127.0.0.1` only, so it is not reachable from outside the server.
Put a reverse proxy in front of it to expose it on a domain.

### Server preparation

Done once from an account with `sudo`. Replace `<server-host>` and `<admin-user>` with the real ones.
The server needs [Docker Engine](https://docs.docker.com/engine/install/), which includes the
`docker compose` plugin.

Create a separate unprivileged user for deployments, with no password, so the only way into the
account is the deploy key:

```bash
sudo adduser --disabled-password data-hub   # Debian/Ubuntu
sudo usermod -aG docker data-hub
```

Membership in the `docker` group is equivalent to root on the host, so this account is only for
deploying this service. Then create the directory the workflow copies into, and the token the
container reads:

```bash
sudo install -d -o data-hub -g data-hub /opt/data-hub
printf 'API_TOKEN=%s\n' "$(openssl rand -hex 32)" | sudo -u data-hub tee /opt/data-hub/.env >/dev/null
sudo chmod 600 /opt/data-hub/.env
```

`compose.yaml` reads `/opt/data-hub/.env` at startup, and the deploy job never touches that file. The
token lives only on the server.

### Deploy key

Generate the key pair on your machine and send the public half over:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/data-hub -N "" -C "data-hub deploy"
scp ~/.ssh/data-hub.pub <admin-user>@<server-host>:/tmp/
```

Install it as the `data-hub` user's only authorized key, on the server:

```bash
sudo install -d -m 700 -o data-hub -g data-hub /home/data-hub/.ssh
sudo install -m 600 -o data-hub -g data-hub /tmp/data-hub.pub /home/data-hub/.ssh/authorized_keys
rm /tmp/data-hub.pub
```

Check it works before handing the key to Actions:

```bash
ssh -i ~/.ssh/data-hub data-hub@<server-host> docker ps
```

### Host key

The workflow pins the server's host key, so `DEPLOY_KNOWN_HOSTS` has to be the real one. Scan it once,
using the exact host string you will put in `DEPLOY_HOST` — an entry scanned for a hostname will not
match a connection made to an IP:

```bash
key=$(ssh-keyscan -t ed25519 <server-host> 2>/dev/null)
printf '%s\n' "$key"                      # DEPLOY_KNOWN_HOSTS
printf '%s\n' "$key" | ssh-keygen -lf -   # its fingerprint
```

Both lines come from that one scan: the first is what you paste into the secret, the second is its
fingerprint. A scan trusts whatever answers, so compare that fingerprint with the key as the server
itself reports it:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

The two `SHA256:` fingerprints must be identical. If they differ, something is answering in the server's
place — do not use the scan.

### Repository secrets

Set these under **Settings → Secrets and variables → Actions**:

| Secret                | Value                                                     |
| --------------------- | --------------------------------------------------------- |
| `DEPLOY_HOST`         | Server hostname or IP, exactly as scanned above            |
| `DEPLOY_USER`         | `data-hub`                                                 |
| `DEPLOY_SSH_KEY`      | Contents of `~/.ssh/data-hub` (the private half)           |
| `DEPLOY_KNOWN_HOSTS`  | The verified host key line from [Host key](#host-key)      |

## Project layout

```
main.py           FastAPI app: bearer auth, routes, startup load and background sync
market_data.py    Builds the btc, xau and btcxau series and keeps them current
binance_spot.py   Paged daily kline fetching from the Binance public API
yahoo_finance.py  Reads the Yahoo Finance CSVs in data/
utils.py          Date helper and the gap filler
data/             Yahoo Finance daily history, as downloaded
```
