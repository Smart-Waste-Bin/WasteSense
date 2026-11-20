from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, me
from app.config import settings
from app.core.errors import add_error_handlers

app = FastAPI(title="SmartBin API")

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
