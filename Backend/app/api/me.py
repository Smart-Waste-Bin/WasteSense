from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.schemas import NOT_LOGGED_IN, MeOut, error_responses
from app.models import User

router = APIRouter(prefix="/api", tags=["me"])


@router.get("/me", response_model=MeOut, responses=error_responses(NOT_LOGGED_IN))
def me(user: User = Depends(get_current_user)):
    return user
