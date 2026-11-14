# Database

PostgreSQL 16 + PostGIS. Models are in `Backend/app/models/`, migrations in `Backend/alembic/`.

## Tables

| Table | What it stores |
| --- | --- |
| `users` | People who log in: admins, supervisors and collectors (argon2 password hash, role). |
| `bins` | Each smart bin: id like `BIN-001`, location (PostGIS point), size, status, latest fill and battery, and `is_physical` (real hardware bin or simulated). |
| `readings` | Every fill-level message from a bin sensor (one row per message, unique per bin and `seq`). |
| `rejected_readings` | Sensor messages we could not accept, kept raw with a reason code for debugging. |
| `alerts` | Bin alerts (due, urgent, offline, battery) and whether they are open, acknowledged or resolved. |
| `trucks` | Collection trucks: plate number, capacity and default collector. |
| `routes` | A planned collection trip: collector, truck, method, distances and timing. |
| `route_stops` | The bins on a route, in order, and whether each was emptied or skipped. |
| `collections` | A bin emptied by a collector, sent from the phone (idempotency key stops double saves). |
| `collector_locations` | GPS points from the collector's phone during a route. |
| `notifications` | In-app messages for one user, read or unread. |
| `settings` | System settings, one row per key (thresholds, depot, notification preferences). |

Fixed value lists (role, status, alert type, ...) are `VARCHAR` + `CHECK`, mirrored in
`Backend/app/models/enums.py`. All timestamps are `timestamptz` in UTC.

## Run the migrations

With the stack running (`docker compose up`):

```bash
docker compose exec backend alembic upgrade head      # build or update the database
docker compose exec backend alembic downgrade base    # remove all our tables
docker compose exec backend alembic check             # models and database match?
```

## Load the sample data

```bash
docker compose exec backend python -m scripts.seed
```

Adds 3 users (`admin@smartbin.test`, `supervisor@smartbin.test`, `collector@smartbin.test`),
one truck, the bins from `Backend/scripts/data/bins.csv`, the depot from
`Backend/scripts/data/depot.json` and the default settings.
Passwords come from `SEED_*_PASSWORD` in the root `.env`. Safe to run more than once.

The system covers the city of Kumasi. Our real hardware bin is at KNUST
(`is_physical` = true); the other bins are simulated city bins.

The seed checks both files first and changes nothing if any coordinate is still `PLACEHOLDER` or `CHECK`,
is not a number, or is outside Kumasi (lat 6.55 to 6.80, lon -1.72 to -1.50). It lists every
problem with its line number.

## Add or move a bin

1. In Google Maps, right-click the spot. The first line of the menu is the coordinates,
   e.g. `6.68712, -1.62458`. Click it to copy.
2. **Lat comes first** (about 6.6 to 6.7), **lon second** (negative, about -1.6).
   Don't swap them: the seed rejects a swapped pair because it lands outside Kumasi.
3. For markets and busy areas, put the pin on the **street edge**, not in the middle of
   the market, so routing snaps to a real road the truck can use.
4. Add a line to `Backend/scripts/data/bins.csv` with the next id (`BIN-011`, `BIN-012`, ...):
   ```
   BIN-011,Name of the spot,6.68712,-1.62458,100,240,false
   ```
   Columns: `id,name,lat,lon,depth_cm,volume_l,is_physical`. `is_physical` is `true` only for
   a real hardware bin.
5. Run the seed again. Existing bins are updated, new ones added. No code change needed.

The depot (where the truck starts and ends) is in `Backend/scripts/data/depot.json`, same rules:
```json
{"name": "Depot name", "lat": 6.68712, "lon": -1.62458}
```
