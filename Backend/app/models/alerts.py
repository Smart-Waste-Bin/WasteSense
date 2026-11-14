import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enum_check
from app.models.enums import AlertState, AlertType


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        enum_check("type", AlertType),
        enum_check("state", AlertState),
        Index("ix_alerts_bin_id_state", "bin_id", "state"),
        # Only one open/acknowledged alert per bin and type.
        Index(
            "uq_alerts_bin_id_type_active",
            "bin_id",
            "type",
            unique=True,
            postgresql_where=text("state <> 'resolved'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    bin_id: Mapped[str] = mapped_column(Text, ForeignKey("bins.id"))
    type: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, server_default=AlertState.OPEN.value)
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_id_is_read", "user_id", "is_read"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    data: Mapped[Any | None] = mapped_column(JSONB)
    is_read: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
