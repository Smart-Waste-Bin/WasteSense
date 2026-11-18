from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, bins, me, stats, ws
from app.config import settings
from app.core import events
from app.core.errors import add_error_handlers
from app.db import SessionLocal
from app.ingest.mqtt_client import Ingestor
from app.realtime.hub import hub
from app.status.scheduler import start_status_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    events.add_listener(hub.on_event)  # BE-05: every event goes to WebSocket clients
    ingestor = Ingestor(SessionLocal) if settings.mqtt_ingest_enabled else None
    if ingestor:
        ingestor.start()
    scheduler = start_status_job() if settings.status_job_enabled else None
    yield
    if scheduler:
        scheduler.shutdown(wait=False)
    if ingestor:
        ingestor.stop()
    events.remove_listener(hub.on_event)


app = FastAPI(title="SmartBin API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
add_error_handlers(app)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(bins.router)
app.include_router(stats.router)
app.include_router(ws.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
