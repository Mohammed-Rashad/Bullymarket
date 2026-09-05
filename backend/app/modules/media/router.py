from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

from app.api.dependencies import CurrentUser, SettingsDependency
from app.modules.media.schemas import ImageUploadResponse
from app.modules.media.service import store_image

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post(
    "/images",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image_route(
    image: Annotated[UploadFile, File()],
    *,
    settings: SettingsDependency,
    _current_user: CurrentUser,
) -> ImageUploadResponse:
    return ImageUploadResponse(image_url=await store_image(image, settings))
