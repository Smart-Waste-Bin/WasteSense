"""BE-05: WebSocket live updates at /ws?token=<access token> (contract section 7)."""

import asyncio
import uuid

from fastapi import APIRouter, WebSocket
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_db
from app.config import settings
from app.core.errors import ApiError
from app.core.tokens import decode_access_token
from app.models import User
from app.realtime.hub import Client, hub

router = APIRouter()

BAD_TOKEN = 4401
PING = {"type": "ping"}


def check_token(websocket: WebSocket, token: str | None) -> tuple[str, str] | None:
    """Return (user_id, role) for a good token, else None.

    The database session is closed straight away, so an open socket never holds a
    database connection.
    """
    if not token:
        return None
    try:
        user_id = uuid.UUID(decode_access_token(token)["sub"])
    except (ApiError, ValueError):
        return None
    make_db = websocket.app.dependency_overrides.get(get_db, get_db)  # tests swap the db
    sessions = make_db()
    db = next(sessions)
    try:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        return str(user.id), user.role
    finally:
        sessions.close()


async def send_events(websocket: WebSocket, client: Client) -> None:
    while True:
        try:
            message = await asyncio.wait_for(client.queue.get(), settings.ws_ping_interval_s)
        except TimeoutError:
            message = PING
        await websocket.send_json(message)


@router.websocket("/ws")
async def live_updates(websocket: WebSocket, token: str | None = None):
    await websocket.accept()
    found = await run_in_threadpool(check_token, websocket, token)
    if found is None:
        await websocket.close(code=BAD_TOKEN)
        return

    user_id, role = found
    client = Client(user_id=user_id, role=role, loop=asyncio.get_running_loop())
    hub.add(client)
    sender = asyncio.create_task(send_events(websocket, client))
    try:
        # Clients don't send anything in v1. This just waits until they go away.
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
    finally:
        hub.remove(client)
        sender.cancel()
