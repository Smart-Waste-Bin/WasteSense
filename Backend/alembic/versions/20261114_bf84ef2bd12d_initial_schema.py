"""initial schema

Revision ID: bf84ef2bd12d
Revises:
Create Date: 2026-11-14 16:11:41.145908
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision: str = "bf84ef2bd12d"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "bins",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("depth_cm", sa.Numeric(), nullable=False),
        sa.Column("volume_l", sa.Numeric(), nullable=False),
        sa.Column("sensor_id", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), server_default="normal", nullable=False),
        sa.Column("maintenance", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("due_threshold", sa.Numeric(), nullable=True),
        sa.Column("urgent_threshold", sa.Numeric(), nullable=True),
        sa.Column("last_fill", sa.Numeric(), nullable=True),
        sa.Column("last_battery", sa.Numeric(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("id ~ '^BIN-[0-9]{3,}$'", name=op.f("ck_bins_id_format")),
        sa.CheckConstraint(
            "status IN ('normal', 'filling', 'due', 'urgent', 'offline', 'maintenance')",
            name=op.f("ck_bins_status"),
        ),
        sa.CheckConstraint("depth_cm > 0", name=op.f("ck_bins_depth_cm_positive")),
        sa.CheckConstraint(
            "last_battery BETWEEN 0 AND 100", name=op.f("ck_bins_last_battery_range")
        ),
        sa.CheckConstraint("last_fill BETWEEN 0 AND 100", name=op.f("ck_bins_last_fill_range")),
        sa.CheckConstraint("volume_l > 0", name=op.f("ck_bins_volume_l_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bins")),
        sa.UniqueConstraint("sensor_id", name=op.f("uq_bins_sensor_id")),
    )
    op.create_index("ix_bins_location", "bins", ["location"], unique=False, postgresql_using="gist")
    op.create_table(
        "rejected_readings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rejected_readings")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'supervisor', 'collector')", name=op.f("ck_users_role")
        ),
        sa.CheckConstraint("email = lower(email)", name=op.f("ck_users_email_lowercase")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("phone", name=op.f("uq_users_phone")),
    )
    op.create_table(
        "alerts",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("bin_id", sa.Text(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("state", sa.String(), server_default="open", nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('open', 'acknowledged', 'resolved')", name=op.f("ck_alerts_state")
        ),
        sa.CheckConstraint(
            "type IN ('due', 'urgent', 'offline', 'battery')", name=op.f("ck_alerts_type")
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"], ["users.id"], name=op.f("fk_alerts_acknowledged_by_users")
        ),
        sa.ForeignKeyConstraint(["bin_id"], ["bins.id"], name=op.f("fk_alerts_bin_id_bins")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index("ix_alerts_bin_id_state", "alerts", ["bin_id", "state"], unique=False)
    op.create_index(
        "uq_alerts_bin_id_type_active",
        "alerts",
        ["bin_id", "type"],
        unique=True,
        postgresql_where=sa.text("state <> 'resolved'"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notifications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(
        "ix_notifications_user_id_is_read", "notifications", ["user_id", "is_read"], unique=False
    )
    op.create_table(
        "readings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("bin_id", sa.Text(), nullable=False),
        sa.Column("fill", sa.Numeric(), nullable=False),
        sa.Column("distance_cm", sa.Numeric(), nullable=False),
        sa.Column("battery", sa.Numeric(), nullable=True),
        sa.Column("rssi", sa.Integer(), nullable=True),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("device_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_late", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_duplicate", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("battery BETWEEN 0 AND 100", name=op.f("ck_readings_battery_range")),
        sa.CheckConstraint("fill BETWEEN 0 AND 100", name=op.f("ck_readings_fill_range")),
        sa.ForeignKeyConstraint(
            ["bin_id"], ["bins.id"], name=op.f("fk_readings_bin_id_bins"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_readings")),
        sa.UniqueConstraint("bin_id", "seq", name=op.f("uq_readings_bin_id_seq")),
    )
    op.create_index(
        "ix_readings_bin_id_device_ts", "readings", ["bin_id", "device_ts"], unique=False
    )
    op.create_table(
        "settings",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by"], ["users.id"], name=op.f("fk_settings_updated_by_users")
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_settings")),
    )
    op.create_table(
        "trucks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("plate_number", sa.Text(), nullable=False),
        sa.Column("capacity_l", sa.Numeric(), nullable=False),
        sa.Column("default_collector_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("capacity_l > 0", name=op.f("ck_trucks_capacity_l_positive")),
        sa.ForeignKeyConstraint(
            ["default_collector_id"],
            ["users.id"],
            name=op.f("fk_trucks_default_collector_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trucks")),
        sa.UniqueConstraint("plate_number", name=op.f("uq_trucks_plate_number")),
    )
    op.create_table(
        "routes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("collector_id", sa.Uuid(), nullable=False),
        sa.Column("truck_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("method", sa.Text(), nullable=False),
        sa.Column("distance_source", sa.String(), nullable=False),
        sa.Column("total_distance_m", sa.Numeric(), nullable=False),
        sa.Column("est_time_s", sa.Numeric(), nullable=False),
        sa.Column("load_l", sa.Numeric(), nullable=False),
        sa.Column("baseline_fixed_m", sa.Numeric(), nullable=True),
        sa.Column("baseline_nearest_m", sa.Numeric(), nullable=True),
        sa.Column("computation_ms", sa.Integer(), nullable=True),
        sa.Column("geometry", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "distance_source IN ('straight_line', 'osrm')", name=op.f("ck_routes_distance_source")
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'cancelled')",
            name=op.f("ck_routes_status"),
        ),
        sa.ForeignKeyConstraint(
            ["collector_id"], ["users.id"], name=op.f("fk_routes_collector_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_routes_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["truck_id"], ["trucks.id"], name=op.f("fk_routes_truck_id_trucks")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routes")),
    )
    op.create_table(
        "collector_locations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("route_id", sa.Uuid(), nullable=False),
        sa.Column("collector_id", sa.Uuid(), nullable=False),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("accuracy_m", sa.Numeric(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["collector_id"], ["users.id"], name=op.f("fk_collector_locations_collector_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["routes.id"],
            name=op.f("fk_collector_locations_route_id_routes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collector_locations")),
    )
    op.create_index(
        "ix_collector_locations_route_id_recorded_at",
        "collector_locations",
        ["route_id", "recorded_at"],
        unique=False,
    )
    op.create_table(
        "route_stops",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("route_id", sa.Uuid(), nullable=False),
        sa.Column("bin_id", sa.Text(), nullable=False),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("eta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("emptied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'emptied', 'skipped')", name=op.f("ck_route_stops_status")
        ),
        sa.ForeignKeyConstraint(["bin_id"], ["bins.id"], name=op.f("fk_route_stops_bin_id_bins")),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["routes.id"],
            name=op.f("fk_route_stops_route_id_routes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_route_stops")),
        sa.UniqueConstraint("route_id", "bin_id", name=op.f("uq_route_stops_route_id_bin_id")),
        sa.UniqueConstraint(
            "route_id", "stop_order", name=op.f("uq_route_stops_route_id_stop_order")
        ),
    )
    op.create_table(
        "collections",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("stop_id", sa.Uuid(), nullable=True),
        sa.Column("bin_id", sa.Text(), nullable=False),
        sa.Column("collector_id", sa.Uuid(), nullable=False),
        sa.Column("emptied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fill_before", sa.Numeric(), nullable=True),
        sa.Column(
            "confirmed_by_sensor", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bin_id"], ["bins.id"], name=op.f("fk_collections_bin_id_bins")),
        sa.ForeignKeyConstraint(
            ["collector_id"], ["users.id"], name=op.f("fk_collections_collector_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["stop_id"], ["route_stops.id"], name=op.f("fk_collections_stop_id_route_stops")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collections")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_collections_idempotency_key")),
    )


def downgrade() -> None:
    # Extensions stay installed: postgis_topology/tiger depend on postgis.
    op.drop_table("collections")
    op.drop_table("route_stops")
    op.drop_index("ix_collector_locations_route_id_recorded_at", table_name="collector_locations")
    op.drop_table("collector_locations")
    op.drop_table("routes")
    op.drop_table("trucks")
    op.drop_table("settings")
    op.drop_index("ix_readings_bin_id_device_ts", table_name="readings")
    op.drop_table("readings")
    op.drop_index("ix_notifications_user_id_is_read", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(
        "uq_alerts_bin_id_type_active",
        table_name="alerts",
        postgresql_where=sa.text("state <> 'resolved'"),
    )
    op.drop_index("ix_alerts_bin_id_state", table_name="alerts")
    op.drop_table("alerts")
    op.drop_table("users")
    op.drop_table("rejected_readings")
    op.drop_index("ix_bins_location", table_name="bins", postgresql_using="gist")
    op.drop_table("bins")
