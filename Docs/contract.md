# SmartBin message and API contract

This file says exactly how the bin, the backend, the web dashboard and the mobile app talk
to each other. If the code and this file disagree, this file wins and the code gets fixed.

## 0. Header

| | |
| --- | --- |
| Version | 1.0 |
| Date | 2026-11-15 |
| Status | Draft - awaiting approval |
| Ticket | SET-03 (FR-04, FR-15) |

### Approval

| Name | Role | Approved | Date |
| --- | --- | --- | --- |
| Joshua | Backend | no | |
| Nana | Frontend (web and mobile) | no | |
| Mujahid | Hardware (firmware) | no | |

### How to change this contract

- Any change goes through a pull request.
- All three people above must approve it.
- The version number goes up: 1.0 -> 1.1 for an added field or endpoint, 2.0 for a change
  that breaks old code (a renamed or removed field, a new required field).
- Update the examples in `Docs/contract/examples/` in the same PR. `Backend/tests/test_contract.py`
  fails if an example and its schema disagree.

## 1. Naming and common rules

**Bin IDs.** `BIN-` then 3 or more digits, upper case. Example: `BIN-001`.
The same ID is used everywhere:

| Where | Example |
| --- | --- |
| Database (`bins.id`) | `BIN-001` |
| MQTT username | `BIN-001` |
| MQTT topic | `bins/BIN-001/readings` |
| Payload `bin_id` | `"bin_id": "BIN-001"` |

**Times.** ISO 8601, UTC, ending in `Z`. Example: `2026-11-07T08:30:00Z`.
Fractions of a second are allowed (`2026-11-07T08:30:00.250Z`). Offsets like `+00:00` are not.

**Units.**

| Quantity | Unit | Example field |
| --- | --- | --- |
| Distance from the sensor | cm | `distance_cm` |
| Fill level | % (0-100) | `fill`, `last_fill` |
| Battery | % (0-100) | `battery`, `last_battery` |
| Signal strength | dBm | `rssi` |
| Volume | litres | `volume_l`, `capacity_l`, `load_l` |
| Distance on routes | metres | `total_distance_m`, `accuracy_m` |
| Durations | seconds | `est_time_s`, `reporting_interval_s` |

The field name ends in its unit when it can be mixed up (`_cm`, `_l`, `_m`, `_s`).

## 2. MQTT

### Broker, ports and login

| Port | Use | Login |
| --- | --- | --- |
| 1883 | Plain MQTT. Dev only (laptops, simulator). | Username and password required |
| 8883 | MQTT over TLS. The real bin uses this. | Username and password required |

- Every client logs in. Anonymous clients are refused.
- A device's username is its bin ID, e.g. `BIN-001`. Its client ID is also its bin ID.
- The backend logs in as `smartbin-backend` (`MQTT_USER` in `.env`).
- The simulator logs in as `smartbin-simulator` (`MQTT_SIM_USER` in `.env`).

### Topics

| Topic | Direction | QoS | Retained | Published by | Subscribed by |
| --- | --- | --- | --- | --- | --- |
| `bins/{bin_id}/readings` | device -> backend | 1 | no | the device (or simulator) | backend |
| `bins/{bin_id}/status` | device -> backend | 1 | yes | the device (or simulator); the broker sends the last will | backend |
| `bins/{bin_id}/emptied` | backend -> simulator (later the device) | 1 | no | backend | simulator, later the device |

QoS 1 means a message can arrive twice. The backend uses `seq` to spot that (section 4).

**`bins/BIN-001/readings`**, one fill reading. The fields are in section 3.
File: `mqtt/reading.json`

```json
{
  "bin_id": "BIN-001",
  "fill": 72,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1042,
  "ts": "2026-11-07T08:30:00Z",
  "fw": "1.0.0"
}
```

**`bins/BIN-001/status`**, published by the device right after it connects (retained, QoS 1).
File: `mqtt/status-online.json`

```json
{
  "state": "online",
  "fw": "1.0.0"
}
```

The device sets this as its last will when it connects (retained, QoS 1). If the device
drops off without saying goodbye, the broker publishes it. File: `mqtt/status-offline.json`

```json
{
  "state": "offline"
}
```

| Field | Type | Required | Allowed values | Meaning |
| --- | --- | --- | --- | --- |
| `state` | string | yes | `online`, `offline` | Is the device connected? |
| `fw` | string | yes when `online` | e.g. `1.0.0` | Firmware version running |

**`bins/BIN-002/emptied`**, sent by the backend when a collector marks a bin as emptied.
The simulator drops that bin's fill to near 0. File: `mqtt/emptied.json`

```json
{
  "bin_id": "BIN-002",
  "emptied_at": "2026-11-07T09:10:00Z",
  "route_id": "7f3c9a2e-4b1d-4e8a-9c2f-1a6b5d3e8f01"
}
```

| Field | Type | Required | Allowed values | Meaning |
| --- | --- | --- | --- | --- |
| `bin_id` | string | yes | bin ID, same as the topic | Which bin was emptied |
| `emptied_at` | string | yes | UTC time | When the collector emptied it |
| `route_id` | string or null | yes | UUID, or `null` if emptied outside a route | The route it was emptied on |

Schemas: `Docs/contract/schemas/reading.schema.json`, `status.schema.json`, `emptied.schema.json`.

### Access rules

These are set in `Backend/Infra/mosquitto/mosquitto.acl`.

| User | Publish (write) | Subscribe (read) |
| --- | --- | --- |
| A device, e.g. `BIN-001` | `bins/BIN-001/readings`, `bins/BIN-001/status` (its own only) | `bins/BIN-001/emptied` (its own only) |
| `smartbin-backend` | `bins/+/emptied` | `bins/#` |
| `smartbin-simulator` | `bins/+/readings`, `bins/+/status` | `bins/+/emptied` |

- A device cannot publish for another bin, and cannot publish to `emptied`.
- The broker can't tell simulated bins from real ones, so the simulator user can write for
  any bin. The simulator only sends for bins with `is_physical = false`.

## 3. Reading message

Topic `bins/{bin_id}/readings`, QoS 1, not retained. One message per reading.
File: `mqtt/reading.json`

```json
{
  "bin_id": "BIN-001",
  "fill": 72,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1042,
  "ts": "2026-11-07T08:30:00Z",
  "fw": "1.0.0"
}
```

| Field | Type | Unit | Required | Allowed values | Meaning |
| --- | --- | --- | --- | --- | --- |
| `bin_id` | string | | yes | `BIN-` + 3 or more digits, same as the topic | Which bin |
| `fill` | integer | % | yes | 0 to 100 | How full the bin is. The device rounds before sending. |
| `distance_cm` | number | cm | yes | more than 0 | Raw distance from the sensor to the rubbish |
| `battery` | integer or null | % | yes | 0 to 100, or `null` | Battery level. `null` when the bin runs on mains power. |
| `rssi` | integer | dBm | yes | below 0, e.g. -61 | Wi-Fi signal strength |
| `seq` | integer | | yes | 1 or more | Reading number. Starts at 1, goes up by 1 for each reading, never goes down, and survives a reboot (saved in flash). |
| `ts` | string | | yes | UTC time | When the reading was **taken**, not when it was sent |
| `fw` | string | | yes | e.g. `1.0.0` | Firmware version |

Rules for the device:

- `fill` is worked out on the device from `distance_cm` and the bin depth, then rounded to a whole number.
- **No valid distance (sensor timeout, echo out of range): the device does not send a reading.**
  It may log the problem locally (serial output). It does not send a fake value.
- **No real time yet (NTP not synced after boot): the device does not send a reading.**
  A wrong `ts` would be rejected as `bad_timestamp`.
- The device reports every `reporting_interval_s` seconds (default 300, from `settings`).
- Extra fields are ignored by the backend. New fields need a contract change.

## 4. Validation rules and reject reasons

The backend checks every reading in this order. The first rule that fails gives the reason code.

| # | Rule | Reason code | Example payload that fails it |
| --- | --- | --- | --- |
| 1 | Not valid JSON | `malformed` | `bad/malformed-not-json.txt` |
| 1 | A required field is missing | `malformed` | `bad/malformed-missing-field.json` (no `seq`) |
| 1 | A field has the wrong type | `malformed` | `bad/malformed-wrong-type.json` (`"fill": "72"`, a string) |
| 1 | `bin_id` in the payload doesn't match the topic | `malformed` | `bad/malformed-topic-mismatch.json` (`BIN-002` sent on `bins/BIN-001/readings`) |
| 2 | `bin_id` is not in the database, or the bin is deleted | `unknown_bin` | `bad/unknown_bin.json` (`BIN-999`, sent on `bins/BIN-999/readings`) |
| 3 | `fill` is a number but not a whole number from 0 to 100 | `fill_out_of_range` | `bad/fill_out_of_range.json` (`"fill": 104`) |
| 4 | `ts` doesn't parse as a UTC time with `Z` | `bad_timestamp` | `bad/bad_timestamp-unparseable.json` (`"07/11/2026 08:30"`) |
| 4 | `ts` is more than 5 minutes in the future | `bad_timestamp` | `bad/bad_timestamp-future.json` (`08:40` received at `08:31`) |

Other field checks (for example `distance_cm` 0 or less, `rssi` 0 or more, `seq` below 1) count as
`malformed`. A `fill` of `72.5` is `fill_out_of_range`, because it is a number but not a whole number.

**Not valid JSON**, sent on `bins/BIN-001/readings` (it is cut off). File: `bad/malformed-not-json.txt`

```text
{"bin_id":"BIN-001","fill":72,
```

**Missing field** (`seq`). File: `bad/malformed-missing-field.json`

```json
{
  "bin_id": "BIN-001",
  "fill": 72,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "ts": "2026-11-07T08:30:00Z",
  "fw": "1.0.0"
}
```

**Wrong type** (`fill` is a string). File: `bad/malformed-wrong-type.json`

```json
{
  "bin_id": "BIN-001",
  "fill": "72",
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1042,
  "ts": "2026-11-07T08:30:00Z",
  "fw": "1.0.0"
}
```

**bin_id doesn't match the topic** (sent on `bins/BIN-001/readings`). File: `bad/malformed-topic-mismatch.json`

```json
{
  "bin_id": "BIN-002",
  "fill": 72,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1042,
  "ts": "2026-11-07T08:30:00Z",
  "fw": "1.0.0"
}
```

**Unknown bin** (sent on `bins/BIN-999/readings`, so the topic matches). File: `bad/unknown_bin.json`

```json
{
  "bin_id": "BIN-999",
  "fill": 72,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1042,
  "ts": "2026-11-07T08:30:00Z",
  "fw": "1.0.0"
}
```

**Fill out of range**. File: `bad/fill_out_of_range.json`

```json
{
  "bin_id": "BIN-001",
  "fill": 104,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1042,
  "ts": "2026-11-07T08:30:00Z",
  "fw": "1.0.0"
}
```

**Timestamp doesn't parse**. File: `bad/bad_timestamp-unparseable.json`

```json
{
  "bin_id": "BIN-001",
  "fill": 72,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1042,
  "ts": "07/11/2026 08:30",
  "fw": "1.0.0"
}
```

**Timestamp in the future** (received at `2026-11-07T08:31:00Z`). File: `bad/bad_timestamp-future.json`

```json
{
  "bin_id": "BIN-001",
  "fill": 72,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1042,
  "ts": "2026-11-07T08:40:00Z",
  "fw": "1.0.0"
}
```

**What happens to a rejected message.** It is saved in `rejected_readings` with:
`topic` (the topic it came in on), `raw` (the payload as received) and `reason` (the code above).
If the payload is not valid JSON, `raw` holds it as a JSON string.

### Not rejections (stored or counted, but flagged)

| Case | Rule | What the backend does | Example |
| --- | --- | --- | --- |
| duplicate | Same (`bin_id`, `seq`) seen before | Ignored (not saved again) and counted | `bad/duplicate.json` (same as `mqtt/reading.json`, sent twice) |
| late | `received_at - ts` is more than 2 x `reporting_interval_s` (default 2 x 300 s = 10 minutes) | Saved with `is_late = true` | `bad/late.json` (taken `08:15`, received `08:31`) |

A late reading still updates the bin's history, but it does not change `last_fill` if a newer reading is already saved.

**Duplicate** (the second copy of `seq` 1042). File: `bad/duplicate.json`

```json
{
  "bin_id": "BIN-001",
  "fill": 72,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1042,
  "ts": "2026-11-07T08:30:00Z",
  "fw": "1.0.0"
}
```

**Late**. File: `bad/late.json`

```json
{
  "bin_id": "BIN-001",
  "fill": 72,
  "distance_cm": 28.4,
  "battery": 95,
  "rssi": -61,
  "seq": 1043,
  "ts": "2026-11-07T08:15:00Z",
  "fw": "1.0.0"
}
```

## 5. REST API conventions

- Base path `/api`. JSON in and out, UTF-8 (`Content-Type: application/json`).
- Field names are `snake_case`, the same as the database columns.
- Times in responses are UTC ISO 8601 with `Z`. The frontend converts them to local time (Ghana is UTC+0 anyway).
- Locations are always `{"lat": 6.6989, "lon": -1.6191}`. Never raw PostGIS (WKB or WKT).
- Numbers are JSON numbers, never strings (`"last_fill": 72`, not `"72"`).

### Auth

Send `Authorization: Bearer <JWT>` on every request. Only two endpoints work without it:
`POST /api/auth/login` and `GET /api/health`.

`POST /api/auth/login`. Request (file `rest/login-request.json`):

```json
{
  "email": "supervisor@smartbin.test",
  "password": "change-me-supervisor"
}
```

Response `200` (file `rest/login-response.json`):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5YTJjNGU2Zi0xYjNkLTRmNTgtYTdjOS0wZTJiNGQ2ZjhhMTAiLCJyb2xlIjoic3VwZXJ2aXNvciIsImV4cCI6MTc5NDA0NjYwMH0.signature",
  "token_type": "bearer",
  "expires_in": 28800,
  "user": {
    "id": "9a2c4e6f-1b3d-4f58-a7c9-0e2b4d6f8a10",
    "name": "Supervisor",
    "email": "supervisor@smartbin.test",
    "role": "supervisor"
  }
}
```

`expires_in` is in seconds (8 hours, one work shift). When the token expires, the API answers `401`
and the app sends the user back to the login screen.

### Errors

Every error has the same shape: `{"error": {"code": "...", "message": "..."}}`.
`message` is plain English the app can show to the user. Apps decide what to do from `code`, never from `message`.

| Code | HTTP status | When | Example file |
| --- | --- | --- | --- |
| `validation_error` | 422 | Bad body or query parameters | `rest/error-validation_error.json` |
| `unauthorized` | 401 | No token, bad token, expired token, wrong password at login | `rest/error-unauthorized.json` |
| `forbidden` | 403 | Logged in, but this role may not do this | `rest/error-forbidden.json` |
| `not_found` | 404 | The thing doesn't exist, or is deleted | `rest/error-not_found.json` |
| `conflict` | 409 | Clashes with existing data (duplicate email, route already started) | `rest/error-conflict.json` |
| `internal_error` | 500 | Bug or server problem | `rest/error-internal_error.json` |

`422`, for `GET /api/bins?size=500`:

```json
{
  "error": {
    "code": "validation_error",
    "message": "size must be between 1 and 100."
  }
}
```

`401`:

```json
{
  "error": {
    "code": "unauthorized",
    "message": "Missing or expired token. Log in again."
  }
}
```

`403`, a collector calls `POST /api/routes`:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Collectors cannot create routes."
  }
}
```

`404`, `GET /api/bins/BIN-999`:

```json
{
  "error": {
    "code": "not_found",
    "message": "Bin BIN-999 not found."
  }
}
```

`409`, `POST /api/users` with an email that is already used:

```json
{
  "error": {
    "code": "conflict",
    "message": "A user with this email already exists."
  }
}
```

`500`:

```json
{
  "error": {
    "code": "internal_error",
    "message": "Something went wrong on the server. Try again later."
  }
}
```

### Paging

- `?page=1&size=20`. `page` starts at 1. `size` is 1 to 100, default 20.
- The response is `{"items": [...], "total": 123}`. `total` is the count of all matching rows, not just this page.

`GET /api/bins?page=1&size=2&sort=-last_fill` (file `rest/bins-page.json`). There are 11 bins, this is the first page of 2:

```json
{
  "items": [
    {
      "id": "BIN-002",
      "name": "Kejetia Market",
      "location": {
        "lat": 6.698635,
        "lon": -1.61914
      },
      "depth_cm": 100,
      "volume_l": 240,
      "sensor_id": null,
      "status": "due",
      "maintenance": false,
      "is_physical": false,
      "due_threshold": null,
      "urgent_threshold": null,
      "last_fill": 78,
      "last_battery": null,
      "last_seen_at": "2026-11-07T08:30:00Z",
      "created_at": "2026-11-01T10:00:00Z"
    },
    {
      "id": "BIN-001",
      "name": "KNUST - SmartBin prototype",
      "location": {
        "lat": 6.672956,
        "lon": -1.565147
      },
      "depth_cm": 100,
      "volume_l": 240,
      "sensor_id": null,
      "status": "due",
      "maintenance": false,
      "is_physical": true,
      "due_threshold": null,
      "urgent_threshold": null,
      "last_fill": 72,
      "last_battery": 95,
      "last_seen_at": "2026-11-07T08:30:00Z",
      "created_at": "2026-11-01T10:00:00Z"
    }
  ],
  "total": 11
}
```

### Filters and sorting

- Filters are query parameters named after the field: `?status=due`, `?is_physical=true`, `?state=open`.
- A filter can take several values separated by commas: `?status=due,urgent`.
- `sort` is a field name. A leading `-` means largest first: `?sort=-last_fill`.
- Example: `GET /api/bins?status=due&sort=-last_fill`.

## 6. Endpoint index (v1 draft)

**Draft: the details (body, filters, exact fields) are fixed in each feature ticket.**
Who can call: A = admin, S = supervisor, C = collector.

| Resource | Method and path | What it does | Who |
| --- | --- | --- | --- |
| auth | `POST /api/auth/login` | Email + password in, token out | anyone |
| me | `GET /api/me` | My own user | A S C |
| me | `PATCH /api/me` | Change my name, phone or password | A S C |
| bins | `GET /api/bins` | List bins (paged, filters, sort) | A S C |
| bins | `GET /api/bins/{id}` | One bin | A S C |
| bins | `POST /api/bins` | Add a bin | A |
| bins | `PATCH /api/bins/{id}` | Edit a bin, set maintenance | A S |
| bins | `DELETE /api/bins/{id}` | Delete a bin (soft delete, sets `deleted_at`) | A |
| readings | `GET /api/bins/{id}/readings` | Fill history, `?from=&to=` (paged) | A S |
| alerts | `GET /api/alerts` | List alerts, `?state=&type=&bin_id=` (paged) | A S |
| alerts | `POST /api/alerts/{id}/acknowledge` | Mark an alert as seen | A S |
| alerts | `POST /api/alerts/{id}/resolve` | Close an alert | A S |
| notifications | `GET /api/notifications` | My notifications, `?is_read=` (paged) | A S C |
| notifications | `POST /api/notifications/{id}/read` | Mark one as read | A S C |
| notifications | `POST /api/notifications/read-all` | Mark all mine as read | A S C |
| routes | `GET /api/routes` | List routes. A collector sees only their own. | A S C |
| routes | `POST /api/routes` | Plan a new route for a collector and truck | A S |
| routes | `GET /api/routes/{id}` | One route with its stops and geometry | A S C (own) |
| routes | `POST /api/routes/{id}/start` | Start the route | C (own) |
| routes | `POST /api/routes/{id}/complete` | Finish the route | C (own) |
| routes | `POST /api/routes/{id}/cancel` | Cancel the route | A S |
| routes | `POST /api/routes/{id}/locations` | Send my GPS position during a route | C (own) |
| stops | `GET /api/routes/{id}/stops` | Stops in order | A S C (own) |
| stops | `PATCH /api/routes/{id}/stops/{stop_id}` | Arrived, skipped (with reason), note, photo | C (own) |
| collections | `POST /api/collections` | Bin emptied (sends `idempotency_key`; triggers MQTT `emptied`) | C |
| collections | `GET /api/collections` | Collection history (paged) | A S |
| collectors | `GET /api/collectors` | Collectors and whether they are on a route now | A S |
| collectors | `GET /api/collectors/{id}/locations` | GPS trail, `?route_id=` | A S |
| trucks | `GET /api/trucks` | List trucks | A S |
| trucks | `POST /api/trucks` | Add a truck | A |
| trucks | `PATCH /api/trucks/{id}` | Edit a truck, set inactive | A |
| users | `GET /api/users` | List users, `?role=` (paged) | A |
| users | `POST /api/users` | Add a user | A |
| users | `PATCH /api/users/{id}` | Edit a user, change role, deactivate | A |
| reports | `GET /api/reports/summary` | Collections, fill and alert counts, `?from=&to=` | A S |
| reports | `GET /api/reports/routes` | Route distance vs the fixed and nearest-bin baselines | A S |
| settings | `GET /api/settings` | All settings (thresholds, interval, depot) | A S |
| settings | `PATCH /api/settings` | Change settings | A |
| health | `GET /api/health` | Is the API up? No login needed. | anyone |

### `GET /api/bins/{id}`

`GET /api/bins/BIN-001`, response `200` (file `rest/bin.json`). Fields come from `Backend/app/models/bins.py`:

```json
{
  "id": "BIN-001",
  "name": "KNUST - SmartBin prototype",
  "location": {
    "lat": 6.672956,
    "lon": -1.565147
  },
  "depth_cm": 100,
  "volume_l": 240,
  "sensor_id": null,
  "status": "due",
  "maintenance": false,
  "is_physical": true,
  "due_threshold": null,
  "urgent_threshold": null,
  "last_fill": 72,
  "last_battery": 95,
  "last_seen_at": "2026-11-07T08:30:00Z",
  "created_at": "2026-11-01T10:00:00Z"
}
```

- `location` is the PostGIS point turned into `lat`/`lon`.
- `due_threshold` and `urgent_threshold` are `null` when the bin uses the value from `settings`.
- `last_battery` is `null` for a bin on mains power or one that has never reported a battery level.
- `deleted_at` is not sent. A deleted bin gives `404`.

### `GET /api/alerts`

`GET /api/alerts?state=open,acknowledged&sort=-created_at`, response `200` (file `rest/alerts-page.json`).
Fields come from `Backend/app/models/alerts.py`:

```json
{
  "items": [
    {
      "id": 41,
      "bin_id": "BIN-001",
      "type": "due",
      "state": "open",
      "message": "BIN-001 is 72% full.",
      "created_at": "2026-11-07T08:30:05Z",
      "acknowledged_by": null,
      "acknowledged_at": null,
      "resolved_at": null
    },
    {
      "id": 38,
      "bin_id": "BIN-007",
      "type": "offline",
      "state": "acknowledged",
      "message": "BIN-007 has not reported for 15 minutes.",
      "created_at": "2026-11-07T07:45:00Z",
      "acknowledged_by": "9a2c4e6f-1b3d-4f58-a7c9-0e2b4d6f8a10",
      "acknowledged_at": "2026-11-07T07:52:10Z",
      "resolved_at": null
    }
  ],
  "total": 2
}
```

| Field | Allowed values |
| --- | --- |
| `type` | `due`, `urgent`, `offline`, `battery` |
| `state` | `open`, `acknowledged`, `resolved` |
| `acknowledged_by` | user UUID, or `null` |

## 7. WebSocket

- URL: `/ws?token=<JWT>` (same token as the REST API).
- A bad or missing token: the server closes the connection with code `4401`.
- Server to client only. Clients don't send messages in v1 (they use the REST API).
- Every event looks like `{"type": "...", "data": {...}, "ts": "..."}`. `ts` is when the server sent it.

### Heartbeat

The server sends this every 25 seconds (file `ws/ping.json`). It is the only message without `data` and `ts`.
No reply is needed. If a client gets nothing for 60 seconds, it reconnects.

```json
{
  "type": "ping"
}
```

### Who gets what

| Event | Admin, supervisor | Collector |
| --- | --- | --- |
| `bin_updated` | all bins | no |
| `alert_created`, `alert_updated` | all | no |
| `route_updated` | all routes | only their own routes |
| `collector_location` | all | no |
| `notification` | their own | their own |

### Events

**`bin_updated`**: a bin's fill, battery, status or last seen time changed. File: `ws/bin_updated.json`

```json
{
  "type": "bin_updated",
  "data": {
    "id": "BIN-001",
    "status": "due",
    "last_fill": 72,
    "last_battery": 95,
    "last_seen_at": "2026-11-07T08:30:00Z"
  },
  "ts": "2026-11-07T08:30:01Z"
}
```

**`alert_created`**: a new alert. `data` is the same as one item from `GET /api/alerts`. File: `ws/alert_created.json`

```json
{
  "type": "alert_created",
  "data": {
    "id": 41,
    "bin_id": "BIN-001",
    "type": "due",
    "state": "open",
    "message": "BIN-001 is 72% full.",
    "created_at": "2026-11-07T08:30:05Z",
    "acknowledged_by": null,
    "acknowledged_at": null,
    "resolved_at": null
  },
  "ts": "2026-11-07T08:30:05Z"
}
```

**`alert_updated`**: an alert was acknowledged or resolved. File: `ws/alert_updated.json`

```json
{
  "type": "alert_updated",
  "data": {
    "id": 41,
    "bin_id": "BIN-001",
    "type": "due",
    "state": "acknowledged",
    "message": "BIN-001 is 72% full.",
    "created_at": "2026-11-07T08:30:05Z",
    "acknowledged_by": "9a2c4e6f-1b3d-4f58-a7c9-0e2b4d6f8a10",
    "acknowledged_at": "2026-11-07T08:34:00Z",
    "resolved_at": null
  },
  "ts": "2026-11-07T08:34:00Z"
}
```

**`route_updated`**: a route started, finished or was cancelled, or one of its stops changed.
`stop` is the stop that changed, or `null`. For the full route, call `GET /api/routes/{id}`. File: `ws/route_updated.json`

```json
{
  "type": "route_updated",
  "data": {
    "id": "7f3c9a2e-4b1d-4e8a-9c2f-1a6b5d3e8f01",
    "status": "in_progress",
    "collector_id": "3b8d1f4a-6c2e-4a97-b5d0-8e1f2a3c4d55",
    "truck_id": "5e7a9c1b-3d5f-4b72-9e4a-6c8e0a2b4d77",
    "started_at": "2026-11-07T08:45:00Z",
    "completed_at": null,
    "stop": {
      "id": "c41e8b07-2d9a-4f63-8e15-9b0a7c2d4e66",
      "bin_id": "BIN-002",
      "stop_order": 1,
      "status": "emptied",
      "emptied_at": "2026-11-07T09:10:00Z"
    }
  },
  "ts": "2026-11-07T09:10:02Z"
}
```

**`collector_location`**: a collector's phone sent a new GPS position. File: `ws/collector_location.json`

```json
{
  "type": "collector_location",
  "data": {
    "route_id": "7f3c9a2e-4b1d-4e8a-9c2f-1a6b5d3e8f01",
    "collector_id": "3b8d1f4a-6c2e-4a97-b5d0-8e1f2a3c4d55",
    "location": {
      "lat": 6.6989,
      "lon": -1.6191
    },
    "accuracy_m": 8,
    "recorded_at": "2026-11-07T09:05:30Z"
  },
  "ts": "2026-11-07T09:05:31Z"
}
```

**`notification`**: a new notification for this user. `data` is the same as one item from
`GET /api/notifications`. File: `ws/notification.json`

```json
{
  "type": "notification",
  "data": {
    "id": 15,
    "type": "route_assigned",
    "title": "New route",
    "body": "You have a new route with 6 stops.",
    "data": {
      "route_id": "7f3c9a2e-4b1d-4e8a-9c2f-1a6b5d3e8f01"
    },
    "is_read": false,
    "created_at": "2026-11-07T08:40:00Z"
  },
  "ts": "2026-11-07T08:40:00Z"
}
```

### Reconnecting

If the connection drops, retry after 1 s, then 2 s, then 5 s, then every 10 s until it works.
After reconnecting, reload the screen's data from the REST API, because events sent while
offline are not replayed. A close with code `4401` means the token is bad: log in again, don't retry.

## 8. Examples check

Every example in this file is also a file in `Docs/contract/examples/`.
`Backend/tests/test_contract.py` checks each one against its schema or shape, and checks that each bad
reading fails with the code above.

| Item | Example file | Example |
| --- | --- | --- |
| Topic `bins/{bin_id}/readings` | `mqtt/reading.json` | yes |
| Topic `bins/{bin_id}/status` (online) | `mqtt/status-online.json` | yes |
| Topic `bins/{bin_id}/status` (offline, last will) | `mqtt/status-offline.json` | yes |
| Topic `bins/{bin_id}/emptied` | `mqtt/emptied.json` | yes |
| Reading message | `mqtt/reading.json` | yes |
| Reject `malformed` (not JSON) | `bad/malformed-not-json.txt` | yes |
| Reject `malformed` (missing field) | `bad/malformed-missing-field.json` | yes |
| Reject `malformed` (wrong type) | `bad/malformed-wrong-type.json` | yes |
| Reject `malformed` (topic mismatch) | `bad/malformed-topic-mismatch.json` | yes |
| Reject `unknown_bin` | `bad/unknown_bin.json` | yes |
| Reject `fill_out_of_range` | `bad/fill_out_of_range.json` | yes |
| Reject `bad_timestamp` (doesn't parse) | `bad/bad_timestamp-unparseable.json` | yes |
| Reject `bad_timestamp` (future) | `bad/bad_timestamp-future.json` | yes |
| Flag duplicate | `bad/duplicate.json` | yes |
| Flag late | `bad/late.json` | yes |
| Login request | `rest/login-request.json` | yes |
| Login response | `rest/login-response.json` | yes |
| Error `validation_error` | `rest/error-validation_error.json` | yes |
| Error `unauthorized` | `rest/error-unauthorized.json` | yes |
| Error `forbidden` | `rest/error-forbidden.json` | yes |
| Error `not_found` | `rest/error-not_found.json` | yes |
| Error `conflict` | `rest/error-conflict.json` | yes |
| Error `internal_error` | `rest/error-internal_error.json` | yes |
| Paging (`GET /api/bins`) | `rest/bins-page.json` | yes |
| Filters and sorting | `rest/bins-page.json`, `rest/alerts-page.json` | yes |
| Times in UTC | every file (checked by the test) | yes |
| Locations as lat/lon | `rest/bin.json` | yes |
| `GET /api/bins/{id}` | `rest/bin.json` | yes |
| `GET /api/alerts` | `rest/alerts-page.json` | yes |
| WebSocket ping | `ws/ping.json` | yes |
| WebSocket `bin_updated` | `ws/bin_updated.json` | yes |
| WebSocket `alert_created` | `ws/alert_created.json` | yes |
| WebSocket `alert_updated` | `ws/alert_updated.json` | yes |
| WebSocket `route_updated` | `ws/route_updated.json` | yes |
| WebSocket `collector_location` | `ws/collector_location.json` | yes |
| WebSocket `notification` | `ws/notification.json` | yes |
