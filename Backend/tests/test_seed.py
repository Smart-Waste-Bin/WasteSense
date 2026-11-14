import json
from pathlib import Path

import pytest
from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.models import Bin, Setting, Truck, User
from scripts.seed import (
    DEFAULT_SETTINGS,
    KUMASI_LAT,
    KUMASI_LON,
    SeedDataError,
    load_bins,
    load_depot,
    seed,
)

TEST_DATA = Path(__file__).parent / "data"
TEST_BINS = load_bins(TEST_DATA / "bins.csv")
TEST_DEPOT = load_depot(TEST_DATA / "depot.json")

PASSWORDS = {"admin": "test-admin", "supervisor": "test-supervisor", "collector": "test-collector"}
HEADER = "id,name,lat,lon,depth_cm,volume_l,is_physical\n"
GOOD_ROW = "BIN-001,Good bin,6.67,-1.57,100,240,true\n"


def count(session: Session, model) -> int:
    return session.execute(select(func.count()).select_from(model)).scalar_one()


def run_seed(engine) -> dict:
    with Session(engine) as session:
        counts = seed(session, PASSWORDS, TEST_BINS, TEST_DEPOT)
        session.commit()
    return counts


def test_seed_twice_gives_same_data(migrated_engine):
    first = run_seed(migrated_engine)
    second = run_seed(migrated_engine)

    assert first["users created"] == 3
    assert first["bins created"] == len(TEST_BINS)
    assert second["users unchanged"] == 3
    assert second["trucks unchanged"] == 1
    assert second["bins unchanged"] == len(TEST_BINS)
    assert second["settings unchanged"] == len(DEFAULT_SETTINGS) + 1

    with Session(migrated_engine) as session:
        assert count(session, User) == 3
        assert count(session, Truck) == 1
        assert count(session, Bin) == len(TEST_BINS)
        assert count(session, Setting) == len(DEFAULT_SETTINGS) + 1

        truck = session.scalar(select(Truck))
        collector = session.scalar(select(User).where(User.role == "collector"))
        assert truck.default_collector_id == collector.id

        assert session.get(Setting, "depot").value == TEST_DEPOT
        physical = session.scalars(select(Bin.id).where(Bin.is_physical)).all()
        assert sorted(physical) == ["BIN-001", "BIN-002"]


def test_bins_are_inside_kumasi(migrated_engine):
    run_seed(migrated_engine)
    with Session(migrated_engine) as session:
        geom = cast(Bin.location, Geometry)
        rows = session.execute(select(Bin.id, func.ST_Y(geom), func.ST_X(geom))).all()

    assert len(rows) == len(TEST_BINS)
    for bin_id, lat, lon in rows:
        assert KUMASI_LAT[0] <= lat <= KUMASI_LAT[1], bin_id
        assert KUMASI_LON[0] <= lon <= KUMASI_LON[1], bin_id


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_placeholder_bin_is_refused(tmp_path):
    csv_file = write(
        tmp_path,
        "bins.csv",
        HEADER + GOOD_ROW + "BIN-002,Kejetia,PLACEHOLDER,-1.62,100,240,false\n",
    )
    with pytest.raises(SeedDataError, match=r"line 3 \(BIN-002\): lat is still PLACEHOLDER"):
        load_bins(csv_file)


def test_bin_outside_kumasi_is_refused(tmp_path):
    csv_file = write(
        tmp_path, "bins.csv", HEADER + GOOD_ROW + "BIN-002,Accra,5.60,-0.19,100,240,false\n"
    )
    with pytest.raises(SeedDataError, match=r"line 3 \(BIN-002\): lat 5.6 is outside Kumasi"):
        load_bins(csv_file)


def test_bin_coordinate_that_is_not_a_number_is_refused(tmp_path):
    csv_file = write(tmp_path, "bins.csv", HEADER + "BIN-001,Typo,6.67,abc,100,240,true\n")
    with pytest.raises(SeedDataError, match="lon 'abc' is not a number"):
        load_bins(csv_file)


def test_more_bins_load_with_no_code_change(tmp_path):
    rows = "".join(f"BIN-{n:03d},Bin {n},6.67,-1.57,100,240,false\n" for n in range(1, 13))
    bins = load_bins(write(tmp_path, "bins.csv", HEADER + rows))
    assert [b["id"] for b in bins][-1] == "BIN-012"


def test_check_placeholder_is_refused_too(tmp_path):
    csv_file = write(tmp_path, "bins.csv", HEADER + "BIN-001,Bantama,CHECK,CHECK,100,240,false\n")
    with pytest.raises(SeedDataError, match="lat is still CHECK"):
        load_bins(csv_file)


def test_placeholder_depot_is_refused(tmp_path):
    depot = {"name": "PLACEHOLDER", "lat": "PLACEHOLDER", "lon": "PLACEHOLDER"}
    with pytest.raises(SeedDataError, match="lat is still PLACEHOLDER"):
        load_depot(write(tmp_path, "depot.json", json.dumps(depot)))


def test_depot_outside_kumasi_is_refused(tmp_path):
    depot = {"name": "Accra depot", "lat": 5.60, "lon": -0.19}
    with pytest.raises(SeedDataError, match="outside Kumasi"):
        load_depot(write(tmp_path, "depot.json", json.dumps(depot)))


def test_real_data_files_are_checked_the_same_way():
    for load in (load_bins, load_depot):
        try:
            load()
        except SeedDataError as error:
            for problem in str(error).splitlines():
                assert "is still" in problem, problem
