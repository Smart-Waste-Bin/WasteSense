# Backend

Python side of SmartBin.

| Folder | What it is |
| --- | --- |
| `app/` | FastAPI server. Receives bin readings over MQTT, stores them in PostgreSQL/PostGIS and serves them to the web and mobile apps. |
| `routing/` | Plans collection routes. `solve_route()` will use OSRM for road distances and OR-Tools for the visit order. Stub for now. |
| `simulator/` | Sends fake bin fill levels over MQTT so we can test without hardware. Only prints the messages for now. |

## Setup

```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
cp .env.example .env            # then fill in the values
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
