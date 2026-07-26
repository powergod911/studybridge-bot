from __future__ import annotations

from io import BytesIO

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_IMAGE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class ImageValidationError(ValueError):
    pass


def validate_image_bytes(
    image_bytes: bytes,
    *,
    declared_content_type: str,
    max_pixels: int = MAX_IMAGE_PIXELS,
) -> None:
    try:
        with Image.open(BytesIO(image_bytes)) as source:
            actual_content_type = ALLOWED_IMAGE_FORMATS.get(source.format or "")
            if actual_content_type is None:
                raise ImageValidationError("Unsupported image format")
            if actual_content_type != declared_content_type:
                raise ImageValidationError("Image content does not match its media type")

            width, height = source.size
            if width <= 0 or height <= 0 or width * height > max_pixels:
                raise ImageValidationError("Image dimensions are too large")

            source.verify()
    except ImageValidationError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageValidationError("Image data is invalid") from exc
