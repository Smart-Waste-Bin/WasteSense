# Backend

Python side of SmartBin.

| Folder | What it is |
| --- | --- |
| `app/` | FastAPI server. Receives bin readings over MQTT, stores them in PostgreSQL/PostGIS and serves them to the web and mobile apps. |
| `routing/` | Plans collection routes. `solve_route()` will use OSRM for road distances and OR-Tools for the visit order. Stub for now. |
| `simulator/` | Sends fake bin fill levels over MQTT so we can test without hardware. Only prints the messages for now. |

## Setup

The easy way is Docker: see "Local setup" in the root README (`docker compose up`).
Settings come from the root `.env` (copy `.env.example` in the repo root), loaded in `app/config.py`.

To run without Docker:

```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt -r requirements-dev.txt
# in the root .env, set the db and mqtt hosts to localhost
```

## Run the API

```bash
uvicorn app.main:app --reload
```

Check it works: open http://127.0.0.1:8000/health, it should return `{"status": "ok"}`.
API docs are at http://127.0.0.1:8000/docs.

The app imports routing directly: `from routing import solve_route`.

## Run the simulator

```bash
python simulator/simulate.py
```

Stop it with Ctrl+C.

## Tests and lint

```bash
pytest          # MQTT tests are skipped if the broker is not running
ruff check .
```

With Docker running: `docker compose exec backend pytest`.
