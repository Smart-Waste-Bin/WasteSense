"""The simulated bins (BE-06). No MQTT here, so it can be tested on its own.

Two clocks:
- simulated time drives the fill model (busy hours, weekends). At --speed 144 it runs 144x.
- `ts` in each reading is the real time the reading was taken. The backend rejects readings
  from the future and flags old ones as late, so `ts` must follow the real clock.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from simulator.profiles import NOISE_CM, PROFILES, Profile, default_profile, rate_per_hour
from simulator.scenario import Scenario

FIRMWARE = "sim-1.0.0"


@dataclass
class Message:
    topic: str
    payload: dict[str, Any]
    retain: bool = False


@dataclass
class SimBin:
    id: str
    name: str
    depth_cm: float
    profile: Profile
    rng: random.Random
    seq: int  # last seq sent; the next reading uses seq + 1
    fill: float = 0.0  # the true fill, before sensor noise
    battery: float = 100.0
    offline: bool = False
    buffer: list[Message] = field(default_factory=list)
    stuck_distance: float | None = None

    def grow(self, when: datetime, hours: float) -> None:
        self.fill += rate_per_hour(self.profile, when) * hours * self.rng.uniform(0.7, 1.3)
        if self.rng.random() < self.profile.jumps_per_day / 24 * hours:
            self.fill += self.rng.uniform(self.profile.jump_min, self.profile.jump_max)
        self.fill = min(self.fill, 100.0)
        self.battery = max(self.battery - 0.02, 5.0)

    def reading(self, taken_at: str, fault: str | None) -> Message:
        distance = self.depth_cm * (1 - self.fill / 100) + self.rng.uniform(-NOISE_CM, NOISE_CM)
        if fault == "stuck":
            if self.stuck_distance is None:
                self.stuck_distance = distance
            distance = self.stuck_distance
        else:
            self.stuck_distance = None
        if fault == "spike" and self.rng.random() < 0.3:
            distance = self.rng.uniform(1, self.depth_cm)  # a bad echo
        distance = round(min(max(distance, 1.0), self.depth_cm), 1)

        fill = round((self.depth_cm - distance) / self.depth_cm * 100)
        if fault == "out_of_range":
            fill = 100 + self.rng.randint(1, 30)  # broken maths on the device: rejected

        self.seq += 1
        payload = {
            "bin_id": self.id,
            "fill": fill,
            "distance_cm": distance,
            "battery": round(self.battery),
            "rssi": self.rng.randint(-80, -55),
            "seq": self.seq,
            "ts": taken_at,
            "fw": FIRMWARE,
        }
        return Message(f"bins/{self.id}/readings", payload)

    def status(self, online: bool) -> Message:
        payload = {"state": "online", "fw": FIRMWARE} if online else {"state": "offline"}
        return Message(f"bins/{self.id}/status", payload, retain=True)


class Simulation:
    def __init__(
        self,
        rows: list[dict[str, Any]],
        scenario: Scenario,
        start: datetime,
        last_seqs: dict[str, int] | None = None,
    ):
        self.scenario = scenario
        self.start = start
        last_seqs = last_seqs or {}
        self.bins: dict[str, SimBin] = {}
        for row in rows:
            seed = f"{scenario.fixed_seed}-{row['id']}" if scenario.fixed_seed is not None else None
            rng = random.Random(seed)
            profile = PROFILES[scenario.profiles.get(row["id"], default_profile(row["name"]))]
            self.bins[row["id"]] = SimBin(
                id=row["id"],
                name=row["name"],
                depth_cm=float(row["depth_cm"]),
                profile=profile,
                rng=rng,
                seq=last_seqs.get(row["id"], 0),
                fill=rng.uniform(0, 40),  # bins start the day part full
            )

    def seqs(self) -> dict[str, int]:
        return {bin_id: the_bin.seq for bin_id, the_bin in self.bins.items()}

    def hello(self) -> list[Message]:
        """Like a device connecting: each bin says it is online."""
        return [the_bin.status(online=True) for the_bin in self.bins.values()]

    def goodbye(self) -> list[Message]:
        """Like the broker's last will when the devices drop off."""
        return [the_bin.status(online=False) for the_bin in self.bins.values()]

    def step(self, sim_time: datetime, taken_at: str) -> list[Message]:
        """One reporting interval for every bin. Returns what to publish, in order."""
        minute = (sim_time - self.start).total_seconds() / 60
        hours = self.scenario.interval_s / 3600
        out: list[Message] = []
        for the_bin in self.bins.values():
            the_bin.grow(sim_time, hours)
            reading = the_bin.reading(taken_at, self.scenario.fault(the_bin.id, minute))

            in_outage = self.scenario.outage(the_bin.id, minute)
            if in_outage and not the_bin.offline:
                the_bin.offline = True
                out.append(the_bin.status(online=False))  # the broker's last will
            elif not in_outage and the_bin.offline:
                # Back online: say hello, then send what was saved during the outage.
                the_bin.offline = False
                out.append(the_bin.status(online=True))
                out.extend(the_bin.buffer)
                the_bin.buffer.clear()

            if the_bin.offline:
                the_bin.buffer.append(reading)  # a real bin keeps readings until it reconnects
            else:
                out.append(reading)
        return out

    def emptied(self, bin_id: str) -> bool:
        """The backend said this bin was emptied: drop it to 0-5 %."""
        the_bin = self.bins.get(bin_id)
        if the_bin is None:
            return False
        the_bin.fill = the_bin.rng.uniform(0, 5)
        return True
