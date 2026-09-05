from pathlib import Path
from tempfile import SpooledTemporaryFile

import pytest
from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import DomainError
from app.modules.media.service import is_managed_image_url, store_image


def upload(content: bytes, filename: str) -> UploadFile:
    file = SpooledTemporaryFile()
    file.write(content)
    file.seek(0)
    return UploadFile(file=file, filename=filename)


@pytest.mark.asyncio
async def test_store_image_uses_detected_type_and_generated_name(tmp_path: Path) -> None:
    image = upload(b"\x89PNG\r\n\x1a\n" + b"image-data", "misleading.jpg")
    settings = Settings(media_root=tmp_path, image_max_bytes=1024)

    image_url = await store_image(image, settings)

    assert image_url.startswith("/media/images/")
    assert image_url.endswith(".png")
    stored = tmp_path / image_url.removeprefix("/media/")
    assert stored.read_bytes().startswith(b"\x89PNG")
    assert is_managed_image_url(image_url)


@pytest.mark.asyncio
async def test_store_image_rejects_unsupported_and_oversized_files(tmp_path: Path) -> None:
    settings = Settings(media_root=tmp_path, image_max_bytes=12)

    with pytest.raises(DomainError, match="JPEG, PNG, WebP, or GIF"):
        await store_image(
            upload(b"not-an-image", "bad.txt"),
            settings,
        )

    with pytest.raises(DomainError, match="12 bytes or smaller"):
        await store_image(
            upload(b"\x89PNG\r\n\x1a\nextra", "large.png"),
            settings,
        )


def test_managed_image_url_does_not_accept_external_or_nested_paths() -> None:
    assert not is_managed_image_url("https://example.com/photo.png")
    assert not is_managed_image_url("/media/images/folder/photo.png")
    assert not is_managed_image_url("/media/images/photo.svg")
