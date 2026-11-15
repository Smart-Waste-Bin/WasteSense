"""Keeps Docs/contract.md and the code from drifting apart.

Every example in Docs/contract/examples/ must match its schema, and every "bad" reading
from section 4 must fail with the reason code the contract gives it.

check_reading() below is the contract's rule order written as code. The real MQTT ingest
(a later ticket) should follow the same order and give the same codes.
"""

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

# Backend/tests/ -> repo root. In Docker, compose mounts ./Docs at /Docs, which is the same path.
DOCS = Path(__file__).resolve().parents[2] / "Docs"
CONTRACT = DOCS / "contract.md"
EXAMPLES = DOCS / "contract" / "examples"
SCHEMAS = DOCS / "contract" / "schemas"

UTC_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
MAX_FUTURE = timedelta(minutes=5)

# The "world" the bad examples are checked against.
KNOWN_BINS = {"BIN-001", "BIN-002"}  # BIN-999 is not in the database
NOW = datetime(2026, 11, 7, 8, 31, tzinfo=UTC)  # received a minute after the example reading
TOPIC = "bins/BIN-001/readings"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator(name: str) -> Draft202012Validator:
    schema = load(SCHEMAS / f"{name}.schema.json")
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def parse_utc(value: str) -> datetime | None:
    if not UTC_TIME.match(value):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def check_reading(topic: str, raw: str, known_bins: set[str], now: datetime) -> str | None:
    """Return the reject reason code, or None if the reading is accepted."""
    try:
        reading = json.loads(raw)
    except ValueError:
        return "malformed"

    errors = list(validator("reading").iter_errors(reading))
    # A fill that is a number but not an integer 0-100 has its own code.
    fill = reading.get("fill") if isinstance(reading, dict) else None
    fill_is_number = isinstance(fill, int | float) and not isinstance(fill, bool)
    other_errors = [e for e in errors if not (list(e.path) == ["fill"] and fill_is_number)]
    if other_errors:
        return "malformed"
    if topic != f"bins/{reading['bin_id']}/readings":
        return "malformed"

    if reading["bin_id"] not in known_bins:
        return "unknown_bin"
    if errors:
        return "fill_out_of_range"

    taken_at = parse_utc(reading["ts"])
    if taken_at is None or taken_at - now > MAX_FUTURE:
        return "bad_timestamp"
    return None


def is_late(ts: str, received_at: datetime, reporting_interval_s: int) -> bool:
    taken_at = parse_utc(ts)
    assert taken_at is not None
    return received_at - taken_at > timedelta(seconds=2 * reporting_interval_s)


# --- MQTT examples match their schemas ---


@pytest.mark.parametrize(
    ("example", "schema"),
    [
        ("mqtt/reading.json", "reading"),
        ("mqtt/status-online.json", "status"),
        ("mqtt/status-offline.json", "status"),
        ("mqtt/emptied.json", "emptied"),
    ],
)
def test_mqtt_example_matches_schema(example, schema):
    validator(schema).validate(load(EXAMPLES / example))


def test_good_reading_is_accepted():
    raw = (EXAMPLES / "mqtt/reading.json").read_text(encoding="utf-8")
    assert check_reading(TOPIC, raw, KNOWN_BINS, NOW) is None


def test_online_status_needs_fw():
    assert not validator("status").is_valid({"state": "online"})


# --- Section 4: each bad reading fails with its reason code ---


@pytest.mark.parametrize(
    ("example", "topic", "reason"),
    [
        ("bad/malformed-not-json.txt", TOPIC, "malformed"),
        ("bad/malformed-missing-field.json", TOPIC, "malformed"),
        ("bad/malformed-wrong-type.json", TOPIC, "malformed"),
        ("bad/malformed-topic-mismatch.json", TOPIC, "malformed"),
        # Sent on its own topic, so it is not malformed. It is just not in the database.
        ("bad/unknown_bin.json", "bins/BIN-999/readings", "unknown_bin"),
        ("bad/fill_out_of_range.json", TOPIC, "fill_out_of_range"),
        ("bad/bad_timestamp-unparseable.json", TOPIC, "bad_timestamp"),
        ("bad/bad_timestamp-future.json", TOPIC, "bad_timestamp"),
    ],
)
def test_bad_reading_fails_with_reason(example, topic, reason):
    raw = (EXAMPLES / example).read_text(encoding="utf-8")
    assert check_reading(topic, raw, KNOWN_BINS, NOW) == reason


def test_duplicate_and_late_are_not_rejected():
    for example in ["bad/duplicate.json", "bad/late.json"]:
        raw = (EXAMPLES / example).read_text(encoding="utf-8")
        assert check_reading(TOPIC, raw, KNOWN_BINS, NOW) is None


def test_late_rule_uses_twice_the_reporting_interval():
    late = load(EXAMPLES / "bad/late.json")
    on_time = load(EXAMPLES / "mqtt/reading.json")
    assert is_late(late["ts"], NOW, reporting_interval_s=300)  # 16 min > 10 min
    assert not is_late(on_time["ts"], NOW, reporting_interval_s=300)  # 1 min


# --- REST and WebSocket examples keep the agreed shapes ---


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("rest/error-*.json")), ids=lambda p: p.stem)
def test_error_example_shape(path):
    body = load(path)
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert path.stem == f"error-{body['error']['code']}"


@pytest.mark.parametrize("name", ["bins-page", "alerts-page"])
def test_page_example_shape(name):
    body = load(EXAMPLES / f"rest/{name}.json")
    assert set(body) == {"items", "total"}
    assert len(body["items"]) <= body["total"]


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("ws/*.json")), ids=lambda p: p.stem)
def test_ws_event_shape(path):
    event = load(path)
    assert event["type"] == path.stem
    if event["type"] == "ping":
        assert event == {"type": "ping"}
    else:
        assert set(event) == {"type", "data", "ts"}
        assert parse_utc(event["ts"]) is not None


def test_every_time_in_examples_is_utc_with_z():
    for path in EXAMPLES.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        for value in re.findall(r'"(\d{4}-\d{2}-\d{2}T[^"]*)"', text):
            if path.name == "bad_timestamp-unparseable.json":
                continue
            assert parse_utc(value) is not None, f"{path.name}: {value}"


def test_every_example_file_is_in_the_contract():
    contract = CONTRACT.read_text(encoding="utf-8")
    for path in EXAMPLES.rglob("*.*"):
        name = path.relative_to(EXAMPLES).as_posix()
        assert name in contract, f"{name} is not shown in Docs/contract.md"
