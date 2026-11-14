"""Publish fake bin fill levels over MQTT so we can test without hardware.

Stub for now: it prints the messages instead of publishing them.
TODO: connect with paho-mqtt using the MQTT_* values from .env.
Run from Backend/: python simulator/simulate.py
"""

import csv
import json
import random
import time
from pathlib import Path

BINS_CSV = Path(__file__).resolve().parents[1] / "scripts" / "data" / "bins.csv"
INTERVAL_SECONDS = 5


def load_bin_ids() -> list[str]:
    with open(BINS_CSV, newline="", encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith("#")]
    return [row["id"] for row in csv.DictReader(lines)]


def main():
    bin_ids = load_bin_ids()
    while True:
        for bin_id in bin_ids:
            payload = {"bin_id": bin_id, "fill_percent": random.randint(0, 100)}
            print(f"bins/{bin_id}/level", json.dumps(payload))
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
