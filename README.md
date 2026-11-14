# WasteSense

Smart Waste Bin is a low-cost IoT system that tells waste collectors which bins are full and plans the shortest route to empty only those bins.. The repo is split into three parts:

## Folders

| Folder | What goes here |
| --- | --- |
| `Firmware/` | Code that runs on the bin's microcontroller: reading the sensors (e.g. fill level) and sending the data to the backend. |
| `Backend/` | The server and API. Receives data from the bins, stores it in the database and serves it to the web and mobile apps. |
| `Backend/Infra/mosquitto/` | MQTT broker config, ACL and the scripts that make dev passwords and certs. |
| `Frontend/` | The user-facing apps. |
| `Frontend/web/` | Web dashboard for monitoring the bins. |
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

6. Run the tests:
   ```bash
   docker compose exec backend pytest
   ```

To stop: `docker compose down`. To also wipe the database: `docker compose down -v`.


## CI

GitHub Actions runs `.github/workflows/ci.yml` on every push, on every pull request into `main`,
and when started by hand.

Only the checks for the folders that changed run. This is true everywhere, `main` included.
Checks for folders you didn't touch show as "skipped", and skipped counts as passing.
If you change `docker-compose.yml`, `.env.example` or anything in `.github/`, every check runs.

| Check | What it does | Runs when this changes |
| --- | --- | --- |
| `lint-python` | Runs `ruff check` and `ruff format --check` on the Python code. | `Backend/` |
| `typecheck-python` | Runs `mypy` with the config in `Backend/pyproject.toml`. | `Backend/` |
| `test` | Starts the database, broker and backend with Docker and runs `pytest` with coverage. | `Backend/` |
| `migrations` | Runs `alembic upgrade head` then `alembic check` against a fresh database. | `Backend/` |
| `docker-build` | Builds the backend Docker image. | `Backend/` |
| `firmware` | Compiles the firmware with `pio run` (no board needed). | `Firmware/` |
| `frontend (Web)` | Runs the web app's npm scripts. | `Frontend/Web/` |
| `frontend (Mobile)` | Runs the mobile app's npm scripts. | `Frontend/Mobile/` |

The last job, `ci-ok`, fails if any of the checks above failed. It is the only check
branch protection requires, so a failing check blocks the merge into `main`.

Frontend: CI runs the npm scripts lint, typecheck, test and build (Web only) if they exist in package.json.

To run everything (e.g. before a demo or at the end of a sprint): go to
Actions -> CI -> Run workflow, and set `run_all` to true.
