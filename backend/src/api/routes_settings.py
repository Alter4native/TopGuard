from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user, require_roles
from src.schemas.domain import Role, SettingsRead, SettingsUpdate
from src.services.store import store


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsRead)
def get_settings(_user=Depends(get_current_user)) -> SettingsRead:
    return store.get_settings()


@router.patch("", response_model=SettingsRead)
def update_settings(
    payload: SettingsUpdate,
    _user=Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
) -> SettingsRead:
    return store.update_settings(payload)

