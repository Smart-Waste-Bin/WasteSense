"""Publish fake bin fill levels over MQTT so we can test without hardware.

Stub for now: it prints the messages instead of publishing them.
TODO: connect with paho-mqtt using the MQTT_* values from .env.
Run from Backend/: python simulator/simulate.py
"""
import json
import random
import time

BIN_IDS = [1, 2, 3]
INTERVAL_SECONDS = 5


def main():
    while True:
        for bin_id in BIN_IDS:
            payload = {"bin_id": bin_id, "fill_percent": random.randint(0, 100)}
            print(f"bins/{bin_id}/level", json.dumps(payload))
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
