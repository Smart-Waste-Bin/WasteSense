from datetime import datetime
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enum_check, range_check
from app.models.enums import BinStatus


class Bin(Base):
    __tablename__ = "bins"
    __table_args__ = (
        CheckConstraint("id ~ '^BIN-[0-9]{3,}$'", name="id_format"),
        CheckConstraint("depth_cm > 0", name="depth_cm_positive"),
        CheckConstraint("volume_l > 0", name="volume_l_positive"),
        enum_check("status", BinStatus),
        range_check("last_fill", 0, 100),
        range_check("last_battery", 0, 100),
        Index("ix_bins_location", "location", postgresql_using="gist"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    # spatial_index=False: the GiST index is declared above with our naming convention.
    location: Mapped[Any] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    depth_cm: Mapped[Decimal] = mapped_column(Numeric)
    volume_l: Mapped[Decimal] = mapped_column(Numeric)
    sensor_id: Mapped[str | None] = mapped_column(Text, unique=True)
    status: Mapped[str] = mapped_column(String, server_default=BinStatus.NORMAL.value)
    maintenance: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    is_physical: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    # NULL means use the value from settings.
    due_threshold: Mapped[Decimal | None] = mapped_column(Numeric)
    urgent_threshold: Mapped[Decimal | None] = mapped_column(Numeric)
    last_fill: Mapped[Decimal | None] = mapped_column(Numeric)
    last_battery: Mapped[Decimal | None] = mapped_column(Numeric)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
