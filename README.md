# WasteSense

Smart waste bin project. The repo is split into three parts:

## Folders

| Folder | What goes here |
| --- | --- |
| `Firmware/` | Code that runs on the bin's microcontroller: reading the sensors (e.g. fill level) and sending the data to the backend. |
| `Backend/` | The server and API. Receives data from the bins, stores it in the database and serves it to the web and mobile apps. |
| `Backend/Infra/mosquitto/` | MQTT broker config, ACL and the scripts that make dev passwords and certs. |
| `Frontend/` | The user-facing apps. |
| `Frontend/Web/` | Web dashboard for monitoring the bins. |
| `Frontend/Mobile/` | Mobile app for users and collectors. |

Each folder will get its own README with setup steps once code is added.

## Local setup

This starts the database (PostgreSQL + PostGIS), the MQTT broker and the backend with one command.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and [Git](https://git-scm.com/).
   On Windows, the commands below work in PowerShell, Git Bash or WSL.

2. Clone the repo:
   ```bash
   git clone https://github.com/Smart-Waste-Bin/WasteSense.git
   cd WasteSense
   ```

3. Get the settings file. Ask the team for the shared `.env` and put it in the repo root
   (it is never committed). Working alone? Make your own and pick your own passwords:
   ```bash
   cp .env.example .env
   ```
   The root `.env` is the only settings file. Docker and the backend both read it.

4. Start everything:
   ```bash
   docker compose up
   ```
   The first start takes a few minutes while images download. A one-off `mqtt-setup` container
   runs first: it makes the dev TLS certs (if missing) and the broker's password file from `.env`,
   then exits. If you change an MQTT password in `.env`, run `docker compose down` and then
   `docker compose up` so the broker picks it up.

   The scripts in `Backend/Infra/mosquitto/` (`make-dev-certs`, `make-passwords`) still work if you
   want to make these files by hand.

5. Check it works (in a second terminal):
   - Open http://localhost:8000/health. It should show `{"status":"ok"}`.
   - Publish as a test device, with a password. This works (no output, no error):
     ```bash
     docker compose exec mqtt mosquitto_pub -h localhost -u bin-001 -P change-me-device -t bins/bin-001/fill -m 42
     ```
     Use your `MQTT_TEST_DEVICE_PASSWORD` from `.env` in place of `change-me-device`.
   - Publish with no password. The broker refuses it (`Connection Refused: not authorised`):
     ```bash
     docker compose exec mqtt mosquitto_pub -h localhost -t bins/bin-001/fill -m 42
     ```

6. Build the database tables and load the sample data (users, truck, Kumasi bins, depot, settings):
   ```bash
   docker compose exec backend alembic upgrade head
   docker compose exec backend python -m scripts.seed
   ```
   The seed user passwords are the `SEED_*_PASSWORD` values in `.env`. The bins and depot come
   from `Backend/scripts/data/bins.csv` and `depot.json`; the seed refuses to run while they still
   have `PLACEHOLDER` or `CHECK` coordinates. Running the seed again is safe: it updates the rows, it does
   not duplicate them.
   See `Docs/database/README.md` for what each table stores.

7. Run the tests:
   ```bash
   docker compose exec backend pytest
   ```

### Changing the database

1. Change or add models in `Backend/app/models/` (new model files must be imported in
   `Backend/app/models/__init__.py`).
2. Make a migration:
   ```bash
   docker compose exec backend alembic revision --autogenerate -m "add xyz to bins"
   ```
3. **Always read and fix the generated file in `Backend/alembic/versions/` before committing.**
   Autogenerate misses or gets wrong: CHECK constraints, partial indexes, PostGIS columns,
   server defaults, and renames (it sees a drop + add, which loses data).
4. Apply it with `docker compose exec backend alembic upgrade head`, and check it can be undone:
   `alembic downgrade -1`, then `alembic upgrade head` again.
5. `docker compose exec backend alembic check` must say no new operations (CI runs it).

To stop: `docker compose down`. To also wipe the database: `docker compose down -v`.

