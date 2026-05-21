from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.schemas.domain import ModelVersionRead
from src.services.store import store


router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[ModelVersionRead])
def list_models(_user=Depends(get_current_user)) -> list[ModelVersionRead]:
    return store.list_models()

