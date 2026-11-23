"""BE-02: every validation rule from Docs/contract.md section 4. No database needed."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.ingest.validation import check_reading, is_late, parse_utc

EXAMPLES = Path(__file__).resolve().parents[2] / "Docs" / "contract" / "examples"
NOW = datetime(2026, 11, 7, 8, 31, tzinfo=UTC)  # a minute after the example reading
TOPIC = "bins/BIN-001/readings"
KNOWN_BINS = {"BIN-001", "BIN-002"}


def known(bin_id: str) -> bool:
    return bin_id in KNOWN_BINS


def good(**changes) -> bytes:
    reading = json.loads((EXAMPLES / "mqtt/reading.json").read_text(encoding="utf-8"))
    reading.update(changes)
    return json.dumps(reading).encode()


def reason(payload: bytes, topic: str = TOPIC, now: datetime = NOW) -> str | None:
    return check_reading(topic, payload, known, now).reason


def test_good_reading_is_accepted():
    result = check_reading(TOPIC, good(), known, NOW)
    assert result.reason is None
    assert result.reading.fill == 72
    assert result.taken_at == datetime(2026, 11, 7, 8, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("example", "topic", "expected"),
    [
        ("bad/malformed-not-json.txt", TOPIC, "malformed"),
        ("bad/malformed-missing-field.json", TOPIC, "malformed"),
        ("bad/malformed-wrong-type.json", TOPIC, "malformed"),
        ("bad/malformed-topic-mismatch.json", TOPIC, "malformed"),
        ("bad/unknown_bin.json", "bins/BIN-999/readings", "unknown_bin"),
        ("bad/fill_out_of_range.json", TOPIC, "fill_out_of_range"),
        ("bad/bad_timestamp-unparseable.json", TOPIC, "bad_timestamp"),
        ("bad/bad_timestamp-future.json", TOPIC, "bad_timestamp"),
    ],
)
def test_contract_bad_examples_give_their_reason(example, topic, expected):
    payload = (EXAMPLES / example).read_bytes()
    assert reason(payload, topic) == expected


# --- Rule 1: malformed ---


def test_not_json_keeps_the_text_as_raw():
    result = check_reading(TOPIC, b'{"bin_id":"BIN-001",', known, NOW)
    assert result.reason == "malformed"
    assert result.raw == '{"bin_id":"BIN-001",'


def test_json_that_is_not_an_object_is_malformed():
    assert reason(b"[1, 2, 3]") == "malformed"


@pytest.mark.parametrize(
    "changes",
    [
        {"distance_cm": 0},
        {"rssi": 0},
        {"seq": 0},
        {"battery": 101},
        {"fw": ""},
        {"fill": True},  # a bool is not a number here
        {"bin_id": "bin-001"},
    ],
)
def test_other_field_checks_are_malformed(changes):
    assert reason(good(**changes)) == "malformed"


def test_topic_that_is_not_a_bin_topic_is_malformed():
    assert reason(good(), topic="something/else") == "malformed"


def test_battery_null_and_extra_fields_are_fine():
    assert reason(good(battery=None, new_field="ignored")) is None


# --- Rule 2: unknown_bin (malformed wins if both fail) ---


def test_unknown_bin():
    assert reason(good(bin_id="BIN-999"), topic="bins/BIN-999/readings") == "unknown_bin"


def test_malformed_is_checked_before_unknown_bin():
    payload = good(bin_id="BIN-999", seq=0)
    assert reason(payload, topic="bins/BIN-999/readings") == "malformed"


# --- Rule 3: fill_out_of_range ---


@pytest.mark.parametrize("fill", [101, -1, 72.5, 104])
def test_fill_out_of_range(fill):
    assert reason(good(fill=fill)) == "fill_out_of_range"


@pytest.mark.parametrize("fill", [0, 100, 72.0])
def test_fill_edges_are_accepted(fill):
    assert reason(good(fill=fill)) is None


def test_unknown_bin_is_checked_before_fill():
    payload = good(bin_id="BIN-999", fill=101)
    assert reason(payload, topic="bins/BIN-999/readings") == "unknown_bin"


# --- Rule 4: bad_timestamp ---


@pytest.mark.parametrize(
    "ts", ["2026-11-07T08:30:00+00:00", "2026-11-07 08:30:00Z", "2026-13-07T08:30:00Z", "now"]
)
def test_timestamp_that_does_not_parse(ts):
    assert reason(good(ts=ts)) == "bad_timestamp"


def test_timestamp_exactly_5_minutes_ahead_is_accepted():
    assert reason(good(ts="2026-11-07T08:36:00Z")) is None


def test_timestamp_more_than_5_minutes_ahead_is_rejected():
    assert reason(good(ts="2026-11-07T08:36:01Z")) == "bad_timestamp"


def test_fractions_of_a_second_are_allowed():
    assert parse_utc("2026-11-07T08:30:00.250Z") is not None


def test_fill_is_checked_before_timestamp():
    assert reason(good(fill=101, ts="bad")) == "fill_out_of_range"


# --- Late (stored, but flagged) ---


def test_late_is_more_than_twice_the_interval():
    taken_at = datetime(2026, 11, 7, 8, 15, tzinfo=UTC)
    assert is_late(taken_at, NOW, reporting_interval_s=300)  # 16 min > 10 min
    assert not is_late(NOW - timedelta(minutes=10), NOW, reporting_interval_s=300)
