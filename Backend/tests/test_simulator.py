"""BE-06: bin simulator (ticket SB-18)."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingest.service import handle_reading, handle_status
from app.ingest.validation import check_reading
from app.models import Bin, Reading
from scripts import seed
from simulator import run
from simulator.engine import Simulation
from simulator.profiles import PROFILES, default_profile, rate_per_hour
from simulator.scenario import Scenario, ScenarioError, Window, load_scenario, parse_scenario

DOCS = Path(__file__).resolve().parents[2] / "Docs" / "contract"
SCENARIOS = Path(__file__).resolve().parents[1] / "simulator" / "scenarios"
MONDAY_6AM = datetime(2026, 11, 16, 6, 0, tzinfo=UTC)
TAKEN = "2026-11-16T06:00:00Z"
ROWS = [
    {"id": "BIN-002", "name": "Kejetia Market", "depth_cm": "100"},
    {"id": "BIN-003", "name": "Ayigya", "depth_cm": "120"},
]


def readings(messages):
    return [m.payload for m in messages if m.topic.endswith("/readings")]


def run_steps(sim, steps, start=MONDAY_6AM, interval_s=300):
    out = []
    for step in range(steps):
        out.append(sim.step(start + timedelta(seconds=step * interval_s), TAKEN))
    return out


# --- Which bins ---


def test_uses_the_seed_file_and_only_simulated_bins():
    rows = run.load_bins()
    assert run.BINS_CSV == seed.BINS_CSV  # the same file the seed reads
    chosen = run.choose_bins(rows, None)
    assert chosen and all(row["is_physical"] == "false" for row in chosen)
    assert "BIN-001" not in {row["id"] for row in chosen}  # the real KNUST bin


def test_asking_for_more_bins_than_the_file_has_is_a_clear_error():
    rows = run.load_bins()
    available = len(run.choose_bins(rows, None))
    assert len(run.choose_bins(rows, available)) == available
    with pytest.raises(run.SetupError, match="Add more rows"):
        run.choose_bins(rows, available + 1)


def test_main_stops_before_connecting_when_setup_is_wrong(capsys):
    assert run.main(["--bins", "999", "--no-register"]) == 1
    assert "Simulator not started" in capsys.readouterr().err


def test_scenario_bins_must_be_in_the_run():
    scenario = Scenario(outages=[Window(bin="BIN-099", start=0, minutes=10)])
    with pytest.raises(run.SetupError, match="BIN-099"):
        run.check_scenario_bins(scenario, ROWS)


# --- Scenario files ---


def test_shipped_scenarios_load():
    assert load_scenario(SCENARIOS / "default.yaml").fixed_seed == 42
    test = load_scenario(SCENARIOS / "outage-and-faulty.yaml")
    assert test.outage("BIN-003", 60) and not test.outage("BIN-003", 90)
    assert test.fault("BIN-004", 0) == "out_of_range"
    assert test.fault("BIN-005", 10_000) == "stuck"  # no minutes = until the end


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"colour": 1}, "unknown option"),
        ({"outages": [{"bin": "BIN-002", "start": 0}]}, "needs `minutes`"),
        ({"outages": [{"bin": "BIN-002", "minutes": 0}]}, "more than 0"),
        ({"faulty": [{"bin": "BIN-002", "mode": "melted"}]}, "mode must be"),
        ({"profiles": {"BIN-002": "stadium"}}, "unknown profile"),
        ({"interval_s": 0}, "interval_s"),
        ({"start": "2026-11-16T06:00:00"}, "time zone"),
    ],
)
def test_bad_scenarios_are_explained(data, message):
    with pytest.raises(ScenarioError, match=message):
        parse_scenario(data)


# --- Fill model and profiles ---


def test_profile_rates_busy_hours_and_weekend():
    market = PROFILES["market"]
    assert rate_per_hour(market, MONDAY_6AM.replace(hour=10)) == 3.0
    assert rate_per_hour(market, MONDAY_6AM.replace(hour=12)) == 6.0
    assert rate_per_hour(market, MONDAY_6AM.replace(hour=18)) == 6.0
    assert rate_per_hour(market, MONDAY_6AM.replace(hour=19)) == 3.0
    saturday = MONDAY_6AM - timedelta(days=2)
    assert rate_per_hour(market, saturday.replace(hour=10)) == 1.5
    assert default_profile("Kejetia Market") == "market"
    assert default_profile("Ayigya") == "residential"


def test_bins_fill_up_over_a_day_and_stay_valid():
    sim = Simulation(ROWS, Scenario(fixed_seed=1), MONDAY_6AM)
    first = readings(sim.step(MONDAY_6AM, TAKEN))
    run_steps(sim, 287, start=MONDAY_6AM + timedelta(minutes=5))
    last = readings(sim.step(MONDAY_6AM + timedelta(hours=24), TAKEN))
    for before, after in zip(first, last, strict=True):
        assert after["fill"] > before["fill"]


def test_readings_match_the_contract_and_pass_the_backend_checks():
    schema = json.loads((DOCS / "schemas/reading.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    sim = Simulation(ROWS, Scenario(fixed_seed=3), MONDAY_6AM)
    for step in run_steps(sim, 50):
        for message in step:
            validator.validate(message.payload)
            result = check_reading(
                message.topic,
                json.dumps(message.payload).encode(),
                lambda bin_id: True,
                datetime(2026, 11, 16, 6, 1, tzinfo=UTC),
            )
            assert result.reason is None, result.reason
            assert 1 <= message.payload["distance_cm"] <= 120


def test_seq_goes_up_by_one_and_continues_after_a_restart():
    sim = Simulation(ROWS, Scenario(fixed_seed=1), MONDAY_6AM, {"BIN-002": 41})
    seqs = [[r["seq"] for r in readings(step)] for step in run_steps(sim, 3)]
    assert seqs == [[42, 1], [43, 2], [44, 3]]
    assert sim.seqs() == {"BIN-002": 44, "BIN-003": 3}


def test_seq_file_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "SEQ_FILE", tmp_path / ".seq.json")
    assert run.load_seqs() == {}
    run.save_seqs({"BIN-002": 7})
    assert run.load_seqs() == {"BIN-002": 7}


# --- Same seed, same data ---


def test_same_seed_gives_the_same_data_twice():
    one = run_steps(Simulation(ROWS, Scenario(fixed_seed=42), MONDAY_6AM), 100)
    two = run_steps(Simulation(ROWS, Scenario(fixed_seed=42), MONDAY_6AM), 100)
    other = run_steps(Simulation(ROWS, Scenario(fixed_seed=43), MONDAY_6AM), 100)
    assert [[m.payload for m in s] for s in one] == [[m.payload for m in s] for s in two]
    assert [[m.payload for m in s] for s in one] != [[m.payload for m in s] for s in other]


def test_a_bin_gets_the_same_data_whatever_else_runs():
    alone = run_steps(Simulation(ROWS[:1], Scenario(fixed_seed=42), MONDAY_6AM), 20)
    together = run_steps(Simulation(ROWS, Scenario(fixed_seed=42), MONDAY_6AM), 20)
    assert [readings(s)[0] for s in alone] == [readings(s)[0] for s in together]


# --- Speed ---


def test_speed_144_runs_24_hours_in_10_minutes():
    scenario = load_scenario(SCENARIOS / "default.yaml")
    args = run.parse_args(["--speed", "144", "--hours", "24"])
    steps = int(args.hours * 3600 / scenario.interval_s)
    step_real_s = scenario.interval_s / args.speed
    assert steps == 288
    assert steps * step_real_s == pytest.approx(600)


# --- Emptied ---


def test_emptied_resets_the_bin_to_0_to_5_percent():
    sim = Simulation(ROWS, Scenario(fixed_seed=1), MONDAY_6AM)
    sim.bins["BIN-002"].fill = 95
    assert sim.emptied("BIN-002")
    assert 0 <= sim.bins["BIN-002"].fill <= 5
    assert not sim.emptied("BIN-404")


def test_emptied_message_from_the_backend_resets_the_bin():
    import threading
    from types import SimpleNamespace

    sim = Simulation(ROWS, Scenario(fixed_seed=1), MONDAY_6AM)
    sim.bins["BIN-002"].fill = 95
    client = run.make_client(sim, threading.Lock())
    payload = (DOCS / "examples/mqtt/emptied.json").read_bytes()  # bin_id BIN-002
    client.on_message(client, None, SimpleNamespace(topic="bins/BIN-002/emptied", payload=payload))
    assert sim.bins["BIN-002"].fill <= 5
    # A message whose bin_id doesn't match the topic is ignored.
    sim.bins["BIN-003"].fill = 95
    client.on_message(client, None, SimpleNamespace(topic="bins/BIN-003/emptied", payload=payload))
    client.on_message(client, None, SimpleNamespace(topic="bins/BIN-003/emptied", payload=b"{"))
    assert sim.bins["BIN-003"].fill == 95


# --- Outage and faulty, through the real backend code ---


@pytest.fixture
def session(migrated_engine):
    with Session(migrated_engine) as session:
        for row in ROWS:
            session.add(
                Bin(
                    id=row["id"],
                    name=row["name"],
                    location="SRID=4326;POINT(-1.6 6.7)",
                    depth_cm=row["depth_cm"],
                    volume_l=240,
                )
            )
        session.commit()
        yield session


def deliver(session, messages, now):
    """Hand the messages to the backend like the MQTT client does. Returns what happened."""
    results = []
    for message in messages:
        payload = json.dumps(message.payload).encode()
        if message.topic.endswith("/readings"):
            results.append(handle_reading(session, message.topic, payload, now))
        else:
            results.append(handle_status(session, message.topic, payload, now))
    return results


def test_outage_makes_a_bin_go_offline_then_recover(session):
    scenario = Scenario(fixed_seed=5, outages=[Window(bin="BIN-003", start=30, minutes=30)])
    sim = Simulation(ROWS, scenario, MONDAY_6AM)
    now = MONDAY_6AM
    statuses = []
    sent = []
    for step in range(20):
        sim_time = MONDAY_6AM + timedelta(minutes=5 * step)
        now = sim_time  # speed 1: real time = simulated time
        messages = sim.step(sim_time, now.isoformat().replace("+00:00", "Z"))
        sent.append([m.payload for m in messages if m.topic.startswith("bins/BIN-003/")])
        deliver(session, messages, now + timedelta(seconds=1))
        session.expire_all()
        statuses.append(session.get(Bin, "BIN-003").status)

    # Minutes 30 to 55 (steps 6 to 11): offline, nothing but the last will is sent.
    assert sent[6] == [{"state": "offline"}]
    assert all(s == [] for s in sent[7:12])
    assert statuses[5] != "offline"
    assert all(s == "offline" for s in statuses[6:12])
    # Minute 60 (step 12): online again, the 6 saved readings, then the new one.
    back = sent[12]
    assert back[0] == {"state": "online", "fw": "sim-1.0.0"}
    assert [r["seq"] for r in back[1:]] == list(range(7, 14))
    assert statuses[12] != "offline"
    # The other bin carried on as normal.
    assert session.get(Bin, "BIN-002").status != "offline"


def test_buffered_readings_are_late_after_a_long_outage(session):
    scenario = Scenario(fixed_seed=5, outages=[Window(bin="BIN-003", start=0, minutes=30)])
    sim = Simulation(ROWS, scenario, MONDAY_6AM)
    results = []
    for step in range(7):
        sim_time = MONDAY_6AM + timedelta(minutes=5 * step)
        messages = [
            m
            for m in sim.step(sim_time, sim_time.isoformat().replace("+00:00", "Z"))
            if m.topic.startswith("bins/BIN-003/")
        ]
        results += deliver(session, messages, sim_time + timedelta(seconds=1))

    late = session.scalars(select(Reading.is_late).where(Reading.bin_id == "BIN-003")).all()
    # Taken at minutes 0-25, sent at 30:01. 0-20 are over 10 min old (2 x interval): late.
    # 25 and the new reading at 30 are on time.
    assert sorted(late) == [False, False, True, True, True, True, True]


def test_faulty_out_of_range_produces_rejected_readings(session):
    scenario = Scenario(
        fixed_seed=5, faulty=[Window(bin="BIN-002", start=0, minutes=15, mode="out_of_range")]
    )
    sim = Simulation(ROWS, scenario, MONDAY_6AM)
    results = []
    for step in range(5):
        sim_time = MONDAY_6AM + timedelta(minutes=5 * step)
        messages = [m for m in sim.step(sim_time, TAKEN) if m.topic.startswith("bins/BIN-002/")]
        results += deliver(session, messages, MONDAY_6AM + timedelta(minutes=1))
    assert results == ["fill_out_of_range"] * 3 + ["stored"] * 2


def test_stuck_sensor_repeats_the_same_distance():
    scenario = Scenario(
        fixed_seed=5, faulty=[Window(bin="BIN-002", start=0, minutes=None, mode="stuck")]
    )
    sim = Simulation(ROWS, scenario, MONDAY_6AM)
    distances = {readings(step)[0]["distance_cm"] for step in run_steps(sim, 30)}
    assert len(distances) == 1


def test_spike_sensor_jumps_around():
    scenario = Scenario(
        fixed_seed=5, faulty=[Window(bin="BIN-002", start=0, minutes=None, mode="spike")]
    )
    fills = [
        readings(step)[0]["fill"] for step in run_steps(Simulation(ROWS, scenario, MONDAY_6AM), 40)
    ]
    jumps = [abs(b - a) for a, b in zip(fills, fills[1:])]
    assert max(jumps) > 20
    assert all(0 <= fill <= 100 for fill in fills)  # spikes are bad data, but not rejected
