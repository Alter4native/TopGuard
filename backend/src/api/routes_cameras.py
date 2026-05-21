from fastapi import APIRouter, Depends

from src.api.errors import not_found_to_http
from src.auth.dependencies import get_current_user, require_roles
from src.schemas.domain import CameraCreate, CameraRead, CameraUpdate, Role
from src.services.store import NotFoundError, store


router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraRead])
def list_cameras(_user=Depends(get_current_user)) -> list[CameraRead]:
    return store.list_cameras()


@router.post("", response_model=CameraRead)
def create_camera(
    payload: CameraCreate,
    _user=Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
) -> CameraRead:
    return store.create_camera(payload)


@router.get("/{camera_id}", response_model=CameraRead)
def get_camera(camera_id: str, _user=Depends(get_current_user)) -> CameraRead:
    try:
        return store.get_camera(camera_id)
    except NotFoundError as exc:
        raise not_found_to_http(exc) from exc


@router.get("/{camera_id}/status", response_model=CameraRead)
def get_camera_status(camera_id: str, _user=Depends(get_current_user)) -> CameraRead:
    try:
        return store.get_camera(camera_id)
    except NotFoundError as exc:
        raise not_found_to_http(exc) from exc


@router.patch("/{camera_id}", response_model=CameraRead)
def update_camera(
    camera_id: str,
    payload: CameraUpdate,
    _user=Depends(require_roles(Role.ADMIN, Role.OPERATOR)),
) -> CameraRead:
    try:
        return store.update_camera(camera_id, payload)
    except NotFoundError as exc:
        raise not_found_to_http(exc) from exc

