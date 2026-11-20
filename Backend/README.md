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

Check it works: open http://127.0.0.1:8000/api/health, it should return `{"status": "ok"}`.
API docs are at http://127.0.0.1:8000/docs.

The app imports routing directly: `from routing import solve_route`.

## Login and roles

Login is in `app/api/auth.py` (`/api/auth/login`, `/refresh`, `/logout`), the current user in
`app/api/me.py`. The API shapes and error codes are in `Docs/contract.md`, section 5.

- Passwords are hashed with argon2 (`app/core/security.py`, pwdlib). Never store, print or log a
  password or a token. Request bodies of `/api/auth/*` are never logged.
- Access tokens are JWTs signed with `JWT_SECRET` (at least 32 characters, or the app won't start).
  Refresh tokens are random strings; only their SHA-256 hash is stored in `refresh_tokens`.
- Phones are stored as `+233XXXXXXXXX` (`app/core/phone.py`).

### Write rule for every new route

Every POST, PUT, PATCH or DELETE route must use one of these (from `app/api/deps.py`):

| What the route writes | Use |
| --- | --- |
| Bins, trucks, planning or cancelling a route, alerts | `Depends(require_role("admin", "supervisor"))` |
| Users, settings | `Depends(require_role("admin"))` |
| A collector's own route (start, complete, stops, GPS, collections) | `Depends(get_current_user)`, then `ensure_own_route_or_staff(user, route)` |

Collectors never write bins, trucks, users or settings: they get `403 forbidden`.
Read routes need at least `Depends(get_current_user)`. Only login, refresh and health are open.

### Manage users

```bash
docker compose exec backend python -m app.cli create-user --name "Ama Mensah" --email ama@example.com --phone 0241234567 --role supervisor
docker compose exec backend python -m app.cli list-users
docker compose exec backend python -m app.cli set-password ama@example.com
docker compose exec backend python -m app.cli deactivate ama@example.com
docker compose exec backend python -m app.cli activate ama@example.com
docker compose exec backend python -m app.cli unlock ama@example.com
```

The password is asked twice with hidden input (at least 8 characters). `set-password` and
`deactivate` also log the user out on every device. The first admin, supervisor and collector come
from the seed (`python -m scripts.seed`, passwords from `SEED_*_PASSWORD` in `.env`).

## Run the simulator

```bash
python simulator/simulate.py
```

Stop it with Ctrl+C.

## Tests and lint

```bash
pytest          # MQTT and database tests are skipped if Docker is not running
ruff check .
mypy .
```

With Docker running: `docker compose exec backend pytest`.
