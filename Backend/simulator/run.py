"""BE-06: run the virtual bins.

Run inside the backend container (it has the packages and the .env values):

    docker compose exec backend python -m simulator.run --speed 144 --hours 24

Options: --bins N (default: every simulated bin in bins.csv), --speed (144 = 24 h in 10 min),
--hours (stop after this many simulated hours; default: run until Ctrl+C),
--scenario (default: simulator/scenarios/default.yaml), --no-register.
"""

import argparse
import csv
import json
import logging
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import paho.mqtt.client as mqtt

from app.config import settings
from simulator.engine import Message, Simulation
from simulator.scenario import ScenarioError, load_scenario

log = logging.getLogger("simulator")

HERE = Path(__file__).resolve().parent
BINS_CSV = HERE.parent / "scripts" / "data" / "bins.csv"  # the same file the seed uses
DEFAULT_SCENARIO = HERE / "scenarios" / "default.yaml"
SEQ_FILE = HERE / ".seq.json"  # last seq per bin; a real device keeps it in flash


class SetupError(Exception):
    pass


# --- Bins ---


def load_bins(path: Path = BINS_CSV) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith("#")]
    return list(csv.DictReader(lines))


def choose_bins(rows: list[dict], count: int | None) -> list[dict]:
    """Only bins with is_physical = false. The real bin sends its own readings."""
    simulated = [row for row in rows if row["is_physical"].strip().lower() != "true"]
    if count is None:
        return simulated
    if count > len(simulated):
        raise SetupError(
            f"--bins {count}, but bins.csv has only {len(simulated)} simulated bins. "
            "Add more rows to Backend/scripts/data/bins.csv (with real Kumasi coordinates), "
            "or ask for fewer bins."
        )
    return simulated[:count]


def check_scenario_bins(scenario, rows: list[dict]) -> None:
    missing = scenario.bins_named() - {row["id"] for row in rows}
    if missing:
        raise SetupError(
            f"The scenario names bins that are not simulated in this run: {sorted(missing)}"
        )


# --- Registering missing bins through the API ---


def api(method: str, path: str, token: str | None = None, body: dict | None = None):
    request = urllib.request.Request(
        settings.sim_api_url.rstrip("/") + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def register_missing_bins(rows: list[dict], last_fills: dict[str, float]) -> list[dict]:
    """Add any bin the backend doesn't know yet. Returns the bins that can be simulated.

    Also fills last_fills with each known bin's last fill, so a restart carries on from there.
    """
    if not settings.seed_supervisor_password:
        raise SetupError(
            "SEED_SUPERVISOR_PASSWORD is not set in .env, so I can't log in to the API."
        )
    status, body = api(
        "POST",
        "/api/auth/login",
        body={"login": settings.sim_api_login, "password": settings.seed_supervisor_password},
    )
    if status != 200:
        raise SetupError(f"API login as {settings.sim_api_login} failed ({status}): {body}")
    token = body["access_token"]

    usable = []
    for row in rows:
        status, known = api("GET", f"/api/bins/{row['id']}", token)
        if status == 200:
            if known.get("last_fill") is not None:
                last_fills[row["id"]] = known["last_fill"]
            usable.append(row)
            continue
        new_bin = {
            "id": row["id"],
            "name": row["name"],
            "location": {"lat": float(row["lat"]), "lng": float(row["lon"])},
            "depth_cm": float(row["depth_cm"]),
            "volume_l": float(row["volume_l"]),
            "is_physical": False,
        }
        status, body = api("POST", "/api/bins", token, new_bin)
        if status == 201:
            log.info("Registered %s through the API", row["id"])
            usable.append(row)
        else:
            # 409: the ID belongs to a deleted bin. Skip it rather than stop the run.
            log.warning("Skipping %s: the API said %s %s", row["id"], status, body)
    return usable


# --- seq that survives a restart ---


def load_seqs() -> dict[str, int]:
    try:
        return json.loads(SEQ_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def save_seqs(seqs: dict[str, int]) -> None:
    SEQ_FILE.write_text(json.dumps(seqs, indent=1), encoding="utf-8")


# --- MQTT ---


def make_client(sim: Simulation, lock: threading.Lock) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="smartbin-simulator")
    client.username_pw_set(settings.mqtt_sim_user, settings.mqtt_sim_password)
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("MQTT login refused: %s", reason_code)
            return
        client.subscribe("bins/+/emptied", qos=1)

    def on_message(client, userdata, message):
        try:
            data = json.loads(message.payload)
            bin_id = message.topic.split("/")[1]
            if data.get("bin_id") != bin_id:
                log.warning(
                    "Ignoring emptied message for %s on %s", data.get("bin_id"), message.topic
                )
                return
            with lock:
                if sim.emptied(bin_id):
                    log.info("%s emptied, fill reset to 0-5 %%", bin_id)
        except (ValueError, AttributeError, IndexError):
            log.warning("Ignoring a bad emptied message on %s", message.topic)

    client.on_connect = on_connect
    client.on_message = on_message
    return client


def publish(client: mqtt.Client, messages: list[Message]) -> None:
    for message in messages:
        client.publish(message.topic, json.dumps(message.payload), qos=1, retain=message.retain)


# --- Main loop ---


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="SmartBin virtual bins (BE-06)")
    parser.add_argument(
        "--bins", type=int, default=None, help="how many simulated bins (default: all)"
    )
    parser.add_argument("--speed", type=float, default=1, help="144 = 24 simulated hours in 10 min")
    parser.add_argument(
        "--hours", type=float, default=None, help="stop after this many simulated hours"
    )
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument(
        "--no-register", action="store_true", help="don't add missing bins via the API"
    )
    args = parser.parse_args(argv)
    if args.speed <= 0 or (args.bins is not None and args.bins < 1):
        parser.error("--speed and --bins must be above 0")
    return args


def stop_on_sigterm(signum, frame):
    raise KeyboardInterrupt


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    args = parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
        rows = choose_bins(load_bins(), args.bins)
        check_scenario_bins(scenario, rows)
    except (SetupError, ScenarioError, OSError) as error:
        print(f"Simulator not started: {error}", file=sys.stderr)
        return 1
    last_fills: dict[str, float] = {}
    if not args.no_register:
        try:
            rows = register_missing_bins(rows, last_fills)
        except (SetupError, OSError) as error:
            # The bins are usually there already (the seed adds them), so carry on.
            log.warning("Could not register missing bins, carrying on without: %s", error)

    sim_start = scenario.start or datetime.now(UTC)
    sim = Simulation(rows, scenario, sim_start, load_seqs(), last_fills)
    lock = threading.Lock()
    client = make_client(sim, lock)
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=30)
    client.loop_start()

    step_real_s = scenario.interval_s / args.speed
    total_steps = None if args.hours is None else int(args.hours * 3600 / scenario.interval_s)
    log.info(
        "%d bins, a reading every %.2f s (= %d simulated s), seed %s",
        len(rows),
        step_real_s,
        scenario.interval_s,
        scenario.fixed_seed,
    )

    # docker compose stop/down sends SIGTERM: stop the same way as Ctrl+C.
    signal.signal(signal.SIGTERM, stop_on_sigterm)
    publish(client, sim.hello())
    began = time.monotonic()
    step = 0
    try:
        while total_steps is None or step < total_steps:
            sim_time = sim_start + timedelta(seconds=step * scenario.interval_s)
            taken_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
            with lock:
                messages = sim.step(sim_time, taken_at)
                save_seqs(sim.seqs())
            publish(client, messages)
            step += 1
            if step % 12 == 0:
                log.info("simulated %s", sim_time.strftime("%a %H:%M"))
            # Sleep until the next step's planned time, so the run doesn't drift.
            time.sleep(max(0.0, began + step * step_real_s - time.monotonic()))
    except KeyboardInterrupt:
        log.info("Stopping")
    finally:
        publish(client, sim.goodbye())
        time.sleep(0.5)  # let the last messages go out
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
