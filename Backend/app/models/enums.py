from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    COLLECTOR = "collector"


class BinStatus(StrEnum):
    NORMAL = "normal"
    FILLING = "filling"
    DUE = "due"
    URGENT = "urgent"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class AlertType(StrEnum):
    DUE = "due"
    URGENT = "urgent"
    OFFLINE = "offline"
    BATTERY = "battery"


class AlertState(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class RouteStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DistanceSource(StrEnum):
    STRAIGHT_LINE = "straight_line"
    OSRM = "osrm"


class StopStatus(StrEnum):
    PENDING = "pending"
    EMPTIED = "emptied"
    SKIPPED = "skipped"
