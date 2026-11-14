"""Run: docker compose exec backend python -m scripts.seed"""

import csv
import json
import re
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import Bin, Setting, Truck, User
from app.models.enums import UserRole

DATA_DIR = Path(__file__).parent / "data"
BINS_CSV = DATA_DIR / "bins.csv"
DEPOT_JSON = DATA_DIR / "depot.json"
BIN_COLUMNS = ["id", "name", "lat", "lon", "depth_cm", "volume_l", "is_physical"]

KUMASI_LAT = (6.55, 6.80)
KUMASI_LON = (-1.72, -1.50)

PLACEHOLDERS = {"PLACEHOLDER", "CHECK"}

USERS = [
    ("Admin", "admin@smartbin.test", UserRole.ADMIN),
    ("Supervisor", "supervisor@smartbin.test", UserRole.SUPERVISOR),
    ("Collector", "collector@smartbin.test", UserRole.COLLECTOR),
]

TRUCK = {"name": "Truck 1", "plate_number": "GT-0001-26", "capacity_l": 2400}

DEFAULT_SETTINGS: dict[str, Any] = {
    "due_threshold": 70,
    "urgent_threshold": 90,
    "battery_low_threshold": 20,
    "reporting_interval_s": 300,
    "offline_timeout_min": 15,
    "service_time_per_stop_s": 120,
    "notification_prefs": {"due": True, "urgent": True, "offline": True, "battery": True},
}


class SeedDataError(Exception):
    pass


def parse_coordinate(value: Any, axis: str, problems: list[str], where: str) -> float | None:
    low, high = KUMASI_LAT if axis == "lat" else KUMASI_LON
    text = str(value).strip()
    if text.upper() in PLACEHOLDERS:
        problems.append(f"{where}: {axis} is still {text}, fill in the real value")
        return None
    try:
        if isinstance(value, bool):
            raise ValueError
        number = float(text)
    except ValueError:
        problems.append(f"{where}: {axis} '{text}' is not a number")
        return None
    if not low <= number <= high:
        problems.append(f"{where}: {axis} {number} is outside Kumasi ({low} to {high})")
        return None
    return number


def parse_positive(value: str, column: str, problems: list[str], where: str) -> Decimal | None:
    try:
        number = Decimal(value)
    except InvalidOperation:
        number = Decimal(0)
    if not number > 0:
        problems.append(f"{where}: {column} '{value}' must be a number above 0")
        return None
    return number


def load_bins(path: Path = BINS_CSV) -> list[dict[str, Any]]:
    with open(path, newline="", encoding="utf-8") as f:
        lines = [(n, line) for n, line in enumerate(f, 1) if line.strip() and line[0] != "#"]
    if not lines or next(csv.reader([lines[0][1]])) != BIN_COLUMNS:
        raise SeedDataError(f"{path.name}: the header must be {','.join(BIN_COLUMNS)}")

    bins: list[dict[str, Any]] = []
    problems: list[str] = []
    seen: set[str] = set()
    for line_no, line in lines[1:]:
        values = [v.strip() for v in next(csv.reader([line]))]
        row = dict(zip(BIN_COLUMNS, values, strict=False))
        where = f"{path.name} line {line_no} ({row.get('id') or 'no id'})"
        if len(values) != len(BIN_COLUMNS):
            problems.append(f"{where}: expected {len(BIN_COLUMNS)} columns, got {len(values)}")
            continue
        if not re.fullmatch(r"BIN-[0-9]{3,}", row["id"]):
            problems.append(f"{where}: id must look like BIN-001")
        elif row["id"] in seen:
            problems.append(f"{where}: id {row['id']} is used twice")
        seen.add(row["id"])
        if not row["name"]:
            problems.append(f"{where}: name is empty")
        if row["is_physical"].lower() not in ("true", "false"):
            problems.append(f"{where}: is_physical must be true or false")
        bins.append(
            {
                "id": row["id"],
                "name": row["name"],
                "lat": parse_coordinate(row["lat"], "lat", problems, where),
                "lon": parse_coordinate(row["lon"], "lon", problems, where),
                "depth_cm": parse_positive(row["depth_cm"], "depth_cm", problems, where),
                "volume_l": parse_positive(row["volume_l"], "volume_l", problems, where),
                "is_physical": row["is_physical"].lower() == "true",
            }
        )
    if problems:
        raise SeedDataError("\n".join(problems))
    return bins


def load_depot(path: Path = DEPOT_JSON) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SeedDataError(f"{path.name}: not valid JSON ({error})") from error
    if not isinstance(data, dict):
        raise SeedDataError(f'{path.name}: must look like {{"name": ..., "lat": ..., "lon": ...}}')

    problems: list[str] = []
    name = str(data.get("name", "")).strip()
    if not name or name.upper() in PLACEHOLDERS:
        problems.append(f"{path.name}: name is still {name or 'empty'}, fill in the real value")
    lat = parse_coordinate(data.get("lat", ""), "lat", problems, path.name)
    lon = parse_coordinate(data.get("lon", ""), "lon", problems, path.name)
    if problems:
        raise SeedDataError("\n".join(problems))
    return {"name": name, "lat": lat, "lon": lon}


def update_fields(obj: Any, values: dict[str, Any]) -> bool:
    changed = False
    for field, value in values.items():
        if getattr(obj, field) != value:
            setattr(obj, field, value)
            changed = True
    return changed


def seed_users(session: Session, passwords: dict[str, str], counts: Counter) -> dict[str, User]:
    users: dict[str, User] = {}
    for name, email, role in USERS:
        password = passwords[role]
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(name=name, email=email, role=role, password_hash=hash_password(password))
            session.add(user)
            counts["users created"] += 1
        else:
            changed = update_fields(user, {"name": name, "role": role, "is_active": True})
            # Only re-hash if the password changed, so a second run changes nothing.
            if not verify_password(password, user.password_hash):
                user.password_hash = hash_password(password)
                changed = True
            counts["users updated" if changed else "users unchanged"] += 1
        users[role] = user
    session.flush()
    return users


def seed_truck(session: Session, collector: User, counts: Counter) -> None:
    values = {**TRUCK, "default_collector_id": collector.id, "is_active": True}
    truck = session.scalar(select(Truck).where(Truck.plate_number == TRUCK["plate_number"]))
    if truck is None:
        session.add(Truck(**values))
        counts["trucks created"] += 1
    else:
        changed = update_fields(truck, values)
        counts["trucks updated" if changed else "trucks unchanged"] += 1


def seed_bins(session: Session, bins: list[dict[str, Any]], counts: Counter) -> None:
    for row in bins:
        lat, lon = row["lat"], row["lon"]
        point = f"SRID=4326;POINT({lon} {lat})"
        values = {
            "name": row["name"],
            "depth_cm": row["depth_cm"],
            "volume_l": row["volume_l"],
            "is_physical": row["is_physical"],
        }
        bin_ = session.get(Bin, row["id"])
        if bin_ is None:
            session.add(Bin(id=row["id"], location=point, **values))
            counts["bins created"] += 1
            continue

        changed = update_fields(bin_, values)
        geom = cast(Bin.location, Geometry)
        current = session.execute(
            select(func.ST_Y(geom), func.ST_X(geom)).where(Bin.id == row["id"])
        ).one()
        if tuple(current) != (lat, lon):
            bin_.location = point
            changed = True
        counts["bins updated" if changed else "bins unchanged"] += 1


def seed_settings(session: Session, depot: dict[str, Any], counts: Counter) -> None:
    for key, value in {**DEFAULT_SETTINGS, "depot": depot}.items():
        setting = session.get(Setting, key)
        if setting is None:
            session.add(Setting(key=key, value=value))
            counts["settings created"] += 1
        elif setting.value != value:
            setting.value = value
            counts["settings updated"] += 1
        else:
            counts["settings unchanged"] += 1


def seed(
    session: Session,
    passwords: dict[str, str],
    bins: list[dict[str, Any]],
    depot: dict[str, Any],
) -> Counter:
    counts: Counter = Counter()
    users = seed_users(session, passwords, counts)
    seed_truck(session, users[UserRole.COLLECTOR], counts)
    seed_bins(session, bins, counts)
    seed_settings(session, depot, counts)
    session.flush()
    return counts


def passwords_from_settings() -> dict[str, str]:
    from app.config import settings

    passwords: dict[str, str] = {
        UserRole.ADMIN: settings.seed_admin_password,
        UserRole.SUPERVISOR: settings.seed_supervisor_password,
        UserRole.COLLECTOR: settings.seed_collector_password,
    }
    missing = [f"SEED_{role.upper()}_PASSWORD" for role, pw in passwords.items() if not pw]
    if missing:
        sys.exit(f"Seed stopped. Set these in the root .env first: {', '.join(missing)}")
    return passwords


def load_data_files() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    problems: list[str] = []
    bins: list[dict[str, Any]] = []
    depot: dict[str, Any] = {}
    try:
        bins = load_bins()
    except SeedDataError as error:
        problems.append(str(error))
    try:
        depot = load_depot()
    except SeedDataError as error:
        problems.append(str(error))
    if problems:
        lines = "\n".join(problems).splitlines()
        sys.exit(
            "Seed stopped, nothing was changed. Fix these in Backend/scripts/data/ first:\n  "
            + "\n  ".join(lines)
        )
    return bins, depot


def main() -> None:
    from app.db import SessionLocal

    passwords = passwords_from_settings()
    bins, depot = load_data_files()
    with SessionLocal() as session:
        counts = seed(session, passwords, bins, depot)
        session.commit()

    print("Seed done:")
    for table in ("users", "trucks", "bins", "settings"):
        print(
            f"  {table:<9} {counts[f'{table} created']} created, "
            f"{counts[f'{table} updated']} updated, {counts[f'{table} unchanged']} unchanged"
        )


if __name__ == "__main__":
    main()
