"""Checks one MQTT reading against Docs/contract.md section 4.

The rules run in the contract's order and the first one that fails gives the reason code:
malformed -> unknown_bin -> fill_out_of_range -> bad_timestamp.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_FUTURE = timedelta(minutes=5)
UTC_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


class ReadingIn(BaseModel):
    """The reading message (contract section 3). Strict, so "72" is not accepted as 72."""

    model_config = ConfigDict(strict=True)

    bin_id: Annotated[str, Field(pattern=r"^BIN-[0-9]{3,}$")]
    # Any number here. Whole number and 0-100 is checked later, it has its own reason code.
    fill: float
    distance_cm: Annotated[float, Field(gt=0)]
    battery: Annotated[int, Field(ge=0, le=100)] | None
    rssi: Annotated[int, Field(lt=0)]
    seq: Annotated[int, Field(ge=1)]
    ts: str
    fw: Annotated[str, Field(min_length=1)]


@dataclass
class CheckResult:
    raw: Any  # what we save in rejected_readings.raw
    reason: str | None = None  # None means the reading is accepted
    reading: ReadingIn | None = None
    taken_at: datetime | None = None


def parse_utc(value: str) -> datetime | None:
    """ISO 8601 UTC ending in Z, or None. Offsets like +00:00 are not allowed."""
    if not UTC_TIME.match(value):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def bin_id_from_topic(topic: str) -> str | None:
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != "bins":
        return None
    return parts[1]


def check_reading(
    topic: str, payload: bytes, bin_exists: Callable[[str], bool], now: datetime
) -> CheckResult:
    text = payload.decode("utf-8", errors="replace")

    # Rule 1: malformed
    try:
        data = json.loads(text)
    except ValueError:
        return CheckResult(raw=text, reason="malformed")
    if not isinstance(data, dict):
        return CheckResult(raw=data, reason="malformed")
    try:
        reading = ReadingIn.model_validate(data)
    except ValidationError:
        return CheckResult(raw=data, reason="malformed")
    if bin_id_from_topic(topic) != reading.bin_id:
        return CheckResult(raw=data, reason="malformed")

    # Rule 2: unknown_bin
    if not bin_exists(reading.bin_id):
        return CheckResult(raw=data, reason="unknown_bin")

    # Rule 3: fill_out_of_range (72.5 counts too, it is not a whole number)
    if not reading.fill.is_integer() or not 0 <= reading.fill <= 100:
        return CheckResult(raw=data, reason="fill_out_of_range")

    # Rule 4: bad_timestamp
    taken_at = parse_utc(reading.ts)
    if taken_at is None or taken_at - now > MAX_FUTURE:
        return CheckResult(raw=data, reason="bad_timestamp")

    return CheckResult(raw=data, reading=reading, taken_at=taken_at)


def is_late(taken_at: datetime, received_at: datetime, reporting_interval_s: int) -> bool:
    return received_at - taken_at > timedelta(seconds=2 * reporting_interval_s)
