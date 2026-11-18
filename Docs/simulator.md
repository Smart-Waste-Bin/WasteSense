# Bin simulator (BE-06)

The simulator makes virtual bins that send readings over MQTT exactly like the real bin,
so the system can be tested and evaluated across Kumasi with only one piece of hardware.

## Run it

The backend container has everything it needs (packages and `.env` values):

```bash
docker compose exec backend python -m simulator.run --speed 144 --hours 24
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--bins N` | every simulated bin | How many bins to run, taken from the top of `bins.csv` |
| `--speed X` | `1` | How much faster than real time. `144` = 24 simulated hours in 10 minutes |
| `--hours H` | run until Ctrl+C | Stop after this many simulated hours |
| `--scenario FILE` | `simulator/scenarios/default.yaml` | Seed, outages and faulty sensors |
| `--no-register` | off | Don't add missing bins through the API |

## Which bins

- Bins come from `Backend/scripts/data/bins.csv`, the same file the seed uses (real Kumasi
  locations). Only bins with `is_physical = false` are simulated; the real KNUST bin sends its own.
- Asking for more bins than the file has is an error. Add rows to `bins.csv` for more bins.
- Bins the backend doesn't know yet are added through `POST /api/bins`, logged in as the seeded
  supervisor (`SEED_SUPERVISOR_PASSWORD` in `.env`).

## What a bin sends

- One reading every `interval_s` simulated seconds (default 300, the contract's reporting interval),
  in the exact contract format (`bins/{id}/readings`, QoS 1).
- `seq` starts at 1 per bin, goes up by 1 and survives a restart (kept in `simulator/.seq.json`,
  like a device keeps it in flash).
- `ts` is the real time the reading was taken. Simulated time only drives the fill model, so
  the backend never sees readings from the future.
- `fill` is worked out from `distance_cm` and the bin depth, the same way the device does it.
- On start each bin sends `online` status; on stop each sends `offline` (like the broker's last will).
- When the backend publishes `bins/{id}/emptied`, that bin drops to 0-5 % fill.

## Fill profiles

Each bin gets a profile. By default a bin with "Market" in its name is a **market** bin and
every other bin is **residential**. A scenario can choose a different profile per bin.

| Profile | Base fill rate | Busy hours | Weekend | Sudden jumps |
| --- | --- | --- | --- | --- |
| market | 3.0 % per hour | x2.0 | x0.5 | about 2 a day, +5 to +15 % each |
| residential | 1.5 % per hour | x1.5 | x0.5 | about 1 a day, +5 to +10 % each |

- **Busy hours:** 12:00-14:00 (lunch) and 17:00-19:00 (evening), Ghana time.
- **Weekend factor:** Saturday and Sunday fill at half the rate.
- **Randomness:** each reading's growth is the rate x 0.7 to 1.3.
- **Sensor noise:** the distance wobbles by up to +-1.5 cm, so `fill` wobbles by about +-1.5 %.
- **Sudden jumps:** someone empties a big load of rubbish into the bin.
- **Start:** each bin starts between 0 and 40 % full.

Over a weekday that adds up to:

- market: 20 h x 3 % + 4 busy h x 6 % = 84 %, plus about 20 % from jumps: full in about a day
  (market bins in Kumasi need emptying daily).
- residential: 20 h x 1.5 % + 4 busy h x 2.25 % = 39 %, plus about 7 % from jumps: about 46 %
  a day, so full in about two days.

At the weekend both fill at half that rate.

## Scenarios

A scenario file (YAML) sets:

| Option | Meaning |
| --- | --- |
| `fixed_seed` | Same seed = the same fill data every run. Remove it for random data. |
| `interval_s` | Simulated seconds between readings |
| `start` | Simulated start time in UTC (e.g. `2026-11-16T06:00:00Z`), or `null` for now |
| `profiles` | Profile per bin, e.g. `{BIN-006: market}` |
| `outages` | `{bin, start, minutes}`: the bin goes offline, keeps its readings and sends them when it is back |
| `faulty` | `{bin, mode, start, minutes}`: a broken sensor. `minutes` left out = until the end |

`start` and `minutes` are simulated minutes after the run starts.

Faulty modes:

| Mode | What the sensor does | What the backend does |
| --- | --- | --- |
| `stuck` | Sends the same distance every time | Stores it (the fill stops changing) |
| `spike` | 30 % of readings are a random bad echo | Stores it (fill jumps around) |
| `out_of_range` | Sends a fill above 100 | Rejects it as `fill_out_of_range` |

`simulator/scenarios/outage-and-faulty.yaml` has one of each, for testing.

## Things to know

- An outage sends the `offline` status at once, so the bin shows Offline straight away even at
  high speed. Readings saved during the outage are flagged **late** only if they are more than
  2 x the reporting interval old in **real** time (the backend's rule). At `--speed 144` a
  30-minute outage lasts 12.5 real seconds, so its readings are not late. To test late
  readings, run at `--speed 1`.
- The fill history (`GET /api/bins/{id}/readings`) uses `ts`, which is real time. At high
  speed a simulated day is squeezed into 10 real minutes of history.
