from __future__ import annotations

import struct
import unittest
import zlib
from io import BytesIO

from PIL import Image

from web.image_validation import ImageValidationError, validate_image_bytes


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    chunk = kind + payload
    return (
        struct.pack(">I", len(payload))
        + chunk
        + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
    )


def png_header(width: int, height: int) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(b""))
        + png_chunk(b"IEND", b"")
    )


class ImageValidationTests(unittest.TestCase):
    def test_accepts_valid_png(self) -> None:
        buffer = BytesIO()
        Image.new("RGB", (20, 10), "white").save(buffer, format="PNG")

        validate_image_bytes(
            buffer.getvalue(),
            declared_content_type="image/png",
        )

    def test_rejects_disguised_content_type(self) -> None:
        buffer = BytesIO()
        Image.new("RGB", (20, 10), "white").save(buffer, format="PNG")

        with self.assertRaisesRegex(ImageValidationError, "media type"):
            validate_image_bytes(
                buffer.getvalue(),
                declared_content_type="image/jpeg",
            )

    def test_rejects_oversized_dimensions_before_decode(self) -> None:
        with self.assertRaisesRegex(ImageValidationError, "dimensions"):
            validate_image_bytes(
                png_header(6000, 6000),
                declared_content_type="image/png",
            )

    def test_rejects_invalid_image_bytes(self) -> None:
        with self.assertRaisesRegex(ImageValidationError, "invalid"):
            validate_image_bytes(
                b"not an image",
                declared_content_type="image/png",
            )


if __name__ == "__main__":
    unittest.main()
