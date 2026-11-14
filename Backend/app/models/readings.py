from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, range_check


class Reading(Base):
    __tablename__ = "readings"
    __table_args__ = (
        range_check("fill", 0, 100),
        range_check("battery", 0, 100),
        UniqueConstraint("bin_id", "seq"),
        Index("ix_readings_bin_id_device_ts", "bin_id", "device_ts"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    bin_id: Mapped[str] = mapped_column(Text, ForeignKey("bins.id", ondelete="RESTRICT"))
    fill: Mapped[Decimal] = mapped_column(Numeric)
    distance_cm: Mapped[Decimal] = mapped_column(Numeric)
    battery: Mapped[Decimal | None] = mapped_column(Numeric)
    rssi: Mapped[int | None] = mapped_column(Integer)
    seq: Mapped[int] = mapped_column(BigInteger)
    device_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_late: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    is_duplicate: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class RejectedReading(Base):
    __tablename__ = "rejected_readings"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    raw: Mapped[Any] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
