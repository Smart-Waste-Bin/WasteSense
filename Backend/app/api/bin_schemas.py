"""Request and response shapes for BE-04 (bins, readings, overview stats)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, overload

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.api.schemas import utc_z

Number = int | float


@overload
def number(value: Decimal) -> Number: ...
@overload
def number(value: Decimal | None) -> Number | None: ...
def number(value: Decimal | None) -> Number | None:
    """Contract rule: numbers are JSON numbers. 100 stays 100, 28.4 stays 28.4."""
    if value is None:
        return None
    return int(value) if value == int(value) else float(value)


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


BIN_EXAMPLE: dict[str, Any] = {
    "id": "BIN-001",
    "name": "KNUST - SmartBin prototype",
    "location": {"lat": 6.672956, "lng": -1.565147},
    "depth_cm": 100,
    "volume_l": 240,
    "sensor_id": None,
    "status": "due",
    "maintenance": False,
    "is_physical": True,
    "due_threshold": None,
    "urgent_threshold": None,
    "last_fill": 72,
    "last_battery": 95,
    "last_seen_at": "2026-11-07T08:30:00Z",
    "created_at": "2026-11-01T10:00:00Z",
}


class BinOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": BIN_EXAMPLE})

    id: str
    name: str
    location: Location
    depth_cm: Number
    volume_l: Number
    sensor_id: str | None
    status: str
    maintenance: bool
    is_physical: bool
    due_threshold: Number | None
    urgent_threshold: Number | None
    last_fill: Number | None
    last_battery: Number | None
    last_seen_at: datetime | None
    created_at: datetime

    @field_serializer("last_seen_at", "created_at")
    def times_utc(self, value: datetime | None) -> str | None:
        return utc_z(value) if value else None


class BinsPage(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [BIN_EXAMPLE],
                "total": 11,
            }
        }
    )

    items: list[BinOut]
    total: int


class BinCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Kejetia Market",
                "location": {"lat": 6.698635, "lng": -1.61914},
                "depth_cm": 100,
                "volume_l": 240,
            }
        },
    )

    # Optional: leave it out and the server picks the next free BIN-NNN.
    # The simulator sends its own IDs from bins.csv.
    id: str | None = Field(default=None, pattern=r"^BIN-[0-9]{3,}$")
    name: str = Field(min_length=1)
    location: Location
    depth_cm: float = Field(gt=0)
    volume_l: float = Field(gt=0)
    sensor_id: str | None = None
    is_physical: bool = False
    due_threshold: float | None = Field(default=None, ge=0, le=100)
    urgent_threshold: float | None = Field(default=None, ge=0, le=100)


class BinUpdate(BaseModel):
    """Only the fields sent are changed. Send null for a threshold to go back to the setting."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"maintenance": True}},
    )

    name: str | None = Field(default=None, min_length=1)
    location: Location | None = None
    depth_cm: float | None = Field(default=None, gt=0)
    volume_l: float | None = Field(default=None, gt=0)
    sensor_id: str | None = None
    maintenance: bool | None = None
    is_physical: bool | None = None
    due_threshold: float | None = Field(default=None, ge=0, le=100)
    urgent_threshold: float | None = Field(default=None, ge=0, le=100)


class RawReadingOut(BaseModel):
    seq: int
    fill: Number
    distance_cm: Number
    battery: Number | None
    rssi: int | None
    ts: datetime
    received_at: datetime
    is_late: bool

    @field_serializer("ts", "received_at")
    def times_utc(self, value: datetime) -> str:
        return utc_z(value)


class HourReadingOut(BaseModel):
    ts: datetime  # start of the hour
    avg_fill: float
    max_fill: Number
    count: int

    @field_serializer("ts")
    def ts_utc(self, value: datetime) -> str:
        return utc_z(value)


class ReadingsPage(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {"ts": "2026-11-07T08:00:00Z", "avg_fill": 70.5, "max_fill": 72, "count": 12},
                    {"ts": "2026-11-07T09:00:00Z", "avg_fill": 74.0, "max_fill": 76, "count": 12},
                ],
                "total": 2,
            }
        }
    )

    items: list[RawReadingOut] | list[HourReadingOut]
    total: int


class OverviewOut(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_bins": 11,
                "needing_collection": 3,
                "offline": 1,
                "collections_today": 4,
                "distance_saved_week_m": 12850,
            }
        }
    )

    total_bins: int
    needing_collection: int
    offline: int
    collections_today: int
    distance_saved_week_m: Number
