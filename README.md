# WasteSense

Smart waste bin project. The repo is split into three parts:

## Folders

| Folder | What goes here |
| --- | --- |
| `Firmware/` | Code that runs on the bin's microcontroller: reading the sensors (e.g. fill level) and sending the data to the backend. |
| `Backend/` | The server and API. Receives data from the bins, stores it in the database and serves it to the web and mobile apps. |
| `Frontend/` | The user-facing apps. |
| `Frontend/Web/` | Web dashboard for monitoring the bins. |
| `Frontend/Mobile/` | Mobile app for users and collectors. |
| `Infra/mosquitto/` | MQTT broker config, ACL and the scripts that make dev passwords and certs. |

Each folder will get its own README with setup steps once code is added.

## Local setup

This starts the database (PostgreSQL + PostGIS), the MQTT broker and the backend with one command.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and [Git](https://git-scm.com/).
   On Windows, run the commands below in **Git Bash** (comes with Git) or WSL.
   PowerShell versions of the two scripts are also given.

2. Clone the repo:
   ```bash
   git clone https://github.com/Smart-Waste-Bin/WasteSense.git
   cd WasteSense
   ```

3. Create your settings file and fill in the values (pick your own passwords):
   ```bash
   cp .env.example .env
   ```
   The root `.env` is the only settings file. Docker and the backend both read it.

4. Make the dev TLS certs and the MQTT passwords:
   ```bash
   bash Infra/mosquitto/make-dev-certs.sh
   bash Infra/mosquitto/make-passwords.sh
   ```
   PowerShell: `.\Infra\mosquitto\make-dev-certs.ps1` and `.\Infra\mosquitto\make-passwords.ps1`.
   The certs are self-signed and for development only. Re-run `make-passwords` whenever you
   change an MQTT password in `.env`, then `docker compose restart mqtt`.

5. Start everything:
   ```bash
   docker compose up
   ```
   The first start takes a few minutes while images download.

6. Check it works (in a second terminal):
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

7. Run the tests:
   ```bash
   docker compose exec backend pytest
   ```

To stop: `docker compose down`. To also wipe the database: `docker compose down -v`.

## Troubleshooting

- **Port 5432 (or 1883, 8000) already in use.** Another Postgres or Mosquitto is running on your
  laptop. Stop it (Windows: Services app, stop "postgresql-x64-..."), or change the left-hand port
  in `docker-compose.yml`, e.g. `"5433:5432"`.
- **Apple Silicon Mac and PostGIS.** The `postgis/postgis` image has no arm64 build. Uncomment
  `platform: linux/amd64` under `db` in `docker-compose.yml`. It runs under emulation, slower but fine.
- **CRLF line endings on Windows.** Errors like `$'\r': command not found` or `bad interpreter`
  mean a script got Windows line endings. `.gitattributes` prevents this for fresh clones. To fix
  an old clone: `git rm --cached -r . && git reset --hard` (commit your work first).
- **mqtt container keeps restarting.** You skipped step 4. Run both scripts, then `docker compose up` again.
