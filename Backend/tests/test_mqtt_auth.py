"""Checks that the broker enforces passwords and the ACL.

Needs the broker running (docker compose up). If it is not reachable these tests
are skipped, so plain `pytest` still works without Docker.
In CI, MQTT_TESTS_REQUIRED=1 turns the skip into a failure.
"""

import os
import socket
import threading
import time
import uuid

import paho.mqtt.client as mqtt
import pytest

from app.config import settings

pytestmark = pytest.mark.integration

HOST = settings.mqtt_host
PORT = settings.mqtt_port


@pytest.fixture(scope="module", autouse=True)
def broker_available():
    try:
        socket.create_connection((HOST, PORT), timeout=2).close()
    except OSError:
        message = f"MQTT broker not reachable at {HOST}:{PORT}"
        if os.environ.get("MQTT_TESTS_REQUIRED") == "1":
            pytest.fail(message)
        pytest.skip(message)


def connect(username=None, password=None):
    """Connect and return (client, reason_code from the broker)."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"test-{uuid.uuid4().hex[:8]}")
    if username:
        client.username_pw_set(username, password)

    got_connack = threading.Event()
    result = {}

    def on_connect(client, userdata, flags, reason_code, properties):
        result["rc"] = reason_code
        got_connack.set()

    client.on_connect = on_connect
    client.connect(HOST, PORT, keepalive=10)
    client.loop_start()
    assert got_connack.wait(5), "no answer from broker"
    return client, result["rc"]


def stop(client):
    client.disconnect()
    client.loop_stop()


@pytest.fixture
def backend_messages():
    """Backend user subscribed to bins/#. Yields the list of received (topic, payload)."""
    client, rc = connect(settings.mqtt_user, settings.mqtt_password)
    assert not rc.is_failure, f"backend could not connect: {rc}"

    messages = []
    subscribed = threading.Event()

    def on_message(client, userdata, msg):
        messages.append((msg.topic, msg.payload.decode()))

    def on_subscribe(client, userdata, mid, reason_codes, properties):
        assert not reason_codes[0].is_failure, "backend not allowed to subscribe to bins/#"
        subscribed.set()

    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.subscribe("bins/#", qos=1)
    assert subscribed.wait(5)

    yield messages
    stop(client)


def publish_as(device, topic, payload):
    client, rc = connect(device, settings.mqtt_test_device_password)
    assert not rc.is_failure, f"{device} could not connect: {rc}"
    client.publish(topic, payload, qos=1).wait_for_publish(5)
    stop(client)


def test_anonymous_connection_is_refused():
    client, rc = connect()
    stop(client)
    assert rc.is_failure


def test_device_cannot_publish_to_another_bin(backend_messages):
    payload = f"spoof-{uuid.uuid4().hex}"
    publish_as("bin-001", "bins/bin-002/fill", payload)
    time.sleep(1.5)
    assert ("bins/bin-002/fill", payload) not in backend_messages


def test_device_can_publish_to_its_own_bin(backend_messages):
    payload = f"ok-{uuid.uuid4().hex}"
    publish_as("bin-001", "bins/bin-001/fill", payload)
    deadline = time.time() + 5
    while time.time() < deadline and ("bins/bin-001/fill", payload) not in backend_messages:
        time.sleep(0.1)
    assert ("bins/bin-001/fill", payload) in backend_messages
