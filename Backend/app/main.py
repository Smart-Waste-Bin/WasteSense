from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import auth, me
from app.config import settings
from app.core import storage
from app.core.errors import add_error_handlers
from app.db import SessionLocal
from app.ingest.mqtt_client import Ingestor


@asynccontextmanager
async def lifespan(app: FastAPI):
    ingestor = Ingestor(SessionLocal) if settings.mqtt_ingest_enabled else None
    if ingestor:
        ingestor.start()
    yield
    if ingestor:
        ingestor.stop()


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

# Local profile photos (STORAGE_BACKEND=local). With S3 the photo URLs point at S3 instead.
if settings.storage_backend == "local":
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    app.mount(storage.MEDIA_URL_PATH, StaticFiles(directory=settings.media_dir), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok"}
