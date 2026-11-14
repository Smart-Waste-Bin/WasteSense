# Import every model here so Base.metadata knows all tables (Alembic reads it).
from app.models.alerts import Alert, Notification
from app.models.base import Base
from app.models.bins import Bin
from app.models.readings import Reading, RejectedReading
from app.models.routes import Collection, CollectorLocation, Route, RouteStop, Truck
from app.models.settings import Setting
from app.models.users import User

__all__ = [
    "Alert",
    "Base",
    "Bin",
    "Collection",
    "CollectorLocation",
    "Notification",
    "Reading",
    "RejectedReading",
    "Route",
    "RouteStop",
    "Setting",
    "Truck",
    "User",
]
