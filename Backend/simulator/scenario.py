"""Scenario files (BE-06). See simulator/scenarios/default.yaml for every option."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

from simulator.profiles import PROFILES

FAULT_MODES = {"stuck", "spike", "out_of_range"}
KEYS = {"fixed_seed", "interval_s", "start", "profiles", "outages", "faulty"}


class ScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class Window:
    """Something that happens to one bin from `start` for `minutes` (simulated minutes)."""

    bin: str
    start: float
    minutes: float | None  # None = until the end of the run
    mode: str | None = None  # only for faulty

    def covers(self, minute: float) -> bool:
        if minute < self.start:
            return False
        return self.minutes is None or minute < self.start + self.minutes


@dataclass
class Scenario:
    fixed_seed: int | None = None
    interval_s: int = 300
    start: datetime | None = None  # simulated start time; None = now
    profiles: dict[str, str] = field(default_factory=dict)
    outages: list[Window] = field(default_factory=list)
    faulty: list[Window] = field(default_factory=list)

    def outage(self, bin_id: str, minute: float) -> bool:
        return any(w.bin == bin_id and w.covers(minute) for w in self.outages)

    def fault(self, bin_id: str, minute: float) -> str | None:
        for window in self.faulty:
            if window.bin == bin_id and window.covers(minute):
                return window.mode
        return None

    def bins_named(self) -> set[str]:
        return set(self.profiles) | {w.bin for w in self.outages + self.faulty}


def window(item: dict, where: str, needs_minutes: bool, with_mode: bool) -> Window:
    if not isinstance(item, dict) or "bin" not in item:
        raise ScenarioError(f"{where}: each entry needs at least `bin`")
    minutes = item.get("minutes")
    if needs_minutes and minutes is None:
        raise ScenarioError(f"{where}: {item['bin']} needs `minutes`")
    if minutes is not None and minutes <= 0:
        raise ScenarioError(f"{where}: {item['bin']} minutes must be more than 0")
    mode = item.get("mode")
    if with_mode and mode not in FAULT_MODES:
        raise ScenarioError(f"{where}: {item['bin']} mode must be one of {sorted(FAULT_MODES)}")
    return Window(bin=item["bin"], start=float(item.get("start", 0)), minutes=minutes, mode=mode)


def parse_scenario(data: dict | None) -> Scenario:
    data = data or {}
    unknown = set(data) - KEYS
    if unknown:
        raise ScenarioError(f"unknown option(s): {sorted(unknown)}. Allowed: {sorted(KEYS)}")

    start = data.get("start")
    if isinstance(start, str):
        start = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if start is not None and start.tzinfo is None:
        raise ScenarioError("start must have a time zone, e.g. 2026-11-16T06:00:00Z")

    profiles = data.get("profiles") or {}
    for bin_id, name in profiles.items():
        if name not in PROFILES:
            raise ScenarioError(f"profiles: {bin_id} has unknown profile {name!r}")

    interval_s = data.get("interval_s", 300)
    if not isinstance(interval_s, int) or interval_s <= 0:
        raise ScenarioError("interval_s must be a whole number of seconds above 0")

    return Scenario(
        fixed_seed=data.get("fixed_seed"),
        interval_s=interval_s,
        start=start,
        profiles=profiles,
        outages=[window(i, "outages", True, False) for i in data.get("outages") or []],
        faulty=[window(i, "faulty", False, True) for i in data.get("faulty") or []],
    )


def load_scenario(path: Path) -> Scenario:
    with open(path, encoding="utf-8") as f:
        return parse_scenario(yaml.safe_load(f))
