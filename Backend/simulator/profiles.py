"""How fast each kind of bin fills (BE-06). Written up for the report in Docs/simulator.md."""

from dataclasses import dataclass
from datetime import datetime

BUSY_HOURS = [(12, 14), (17, 19)]  # lunch and evening rush, Ghana time (= UTC)
WEEKEND_FACTOR = 0.5
NOISE_CM = 1.5  # the ultrasonic sensor wobbles by up to +-1.5 cm


@dataclass(frozen=True)
class Profile:
    name: str
    base_rate: float  # % per hour on a normal weekday hour
    busy_multiplier: float  # x base_rate during BUSY_HOURS
    jumps_per_day: float  # how often someone dumps a big load of rubbish in at once
    jump_min: float  # size of that jump in %
    jump_max: float


PROFILES = {
    "market": Profile(
        "market", base_rate=3.0, busy_multiplier=2.0, jumps_per_day=2, jump_min=5, jump_max=15
    ),
    "residential": Profile(
        "residential", base_rate=1.5, busy_multiplier=1.5, jumps_per_day=1, jump_min=5, jump_max=10
    ),
}


def default_profile(bin_name: str) -> str:
    return "market" if "market" in bin_name.lower() else "residential"


def is_busy(when: datetime) -> bool:
    return any(start <= when.hour < end for start, end in BUSY_HOURS)


def rate_per_hour(profile: Profile, when: datetime) -> float:
    rate = profile.base_rate
    if is_busy(when):
        rate *= profile.busy_multiplier
    if when.weekday() >= 5:  # Saturday, Sunday
        rate *= WEEKEND_FACTOR
    return rate
