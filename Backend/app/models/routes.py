import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enum_check
from app.models.enums import DistanceSource, RouteStatus, StopStatus


class Truck(Base):
    __tablename__ = "trucks"
    __table_args__ = (CheckConstraint("capacity_l > 0", name="capacity_l_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text)
    plate_number: Mapped[str] = mapped_column(Text, unique=True)
    capacity_l: Mapped[Decimal] = mapped_column(Numeric)
    default_collector_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        enum_check("status", RouteStatus),
        enum_check("distance_source", DistanceSource),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    collector_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    truck_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("trucks.id"))
    status: Mapped[str] = mapped_column(String, server_default=RouteStatus.PENDING.value)
    method: Mapped[str] = mapped_column(Text)
    distance_source: Mapped[str] = mapped_column(String)
    total_distance_m: Mapped[Decimal] = mapped_column(Numeric)
    est_time_s: Mapped[Decimal] = mapped_column(Numeric)
    load_l: Mapped[Decimal] = mapped_column(Numeric)
    baseline_fixed_m: Mapped[Decimal | None] = mapped_column(Numeric)
    baseline_nearest_m: Mapped[Decimal | None] = mapped_column(Numeric)
    computation_ms: Mapped[int | None] = mapped_column(Integer)
    geometry: Mapped[Any | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RouteStop(Base):
    __tablename__ = "route_stops"
    __table_args__ = (
        enum_check("status", StopStatus),
        UniqueConstraint("route_id", "stop_order"),
        UniqueConstraint("route_id", "bin_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    route_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("routes.id", ondelete="CASCADE"))
    bin_id: Mapped[str] = mapped_column(Text, ForeignKey("bins.id"))
    stop_order: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, server_default=StopStatus.PENDING.value)
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emptied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    skip_reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    stop_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("route_stops.id"))
    bin_id: Mapped[str] = mapped_column(Text, ForeignKey("bins.id"))
    collector_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    emptied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fill_before: Mapped[Decimal | None] = mapped_column(Numeric)
    confirmed_by_sensor: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CollectorLocation(Base):
    __tablename__ = "collector_locations"
    __table_args__ = (
        Index("ix_collector_locations_route_id_recorded_at", "route_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    route_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("routes.id", ondelete="CASCADE"))
    collector_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
