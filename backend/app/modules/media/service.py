import re
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import DomainError


def _image_extension(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


async def store_image(upload: UploadFile, settings: Settings) -> str:
    content = await upload.read(settings.image_max_bytes + 1)
    await upload.close()
    if not content:
        raise DomainError("empty_image", "Choose a non-empty image file")
    if len(content) > settings.image_max_bytes:
        limit = (
            f"{settings.image_max_bytes // (1024 * 1024)} MB"
            if settings.image_max_bytes >= 1024 * 1024
            else f"{settings.image_max_bytes} bytes"
        )
        raise DomainError("image_too_large", f"Images must be {limit} or smaller", 413)
    extension = _image_extension(content)
    if extension is None:
        raise DomainError(
            "invalid_image_type",
            "Use a JPEG, PNG, WebP, or GIF image",
            415,
        )

    image_directory = settings.media_root / "images"
    image_directory.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{extension}"
    target = image_directory / filename
    target.write_bytes(content)
    return f"/media/images/{filename}"


def is_managed_image_url(value: str | None) -> bool:
    if value is None:
        return True
    return re.fullmatch(
        r"/media/images/[0-9a-f]{32}\.(?:jpg|png|webp|gif)", value
    ) is not None
