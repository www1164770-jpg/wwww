from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import struct
import tempfile
import unittest

from backend.crawler.assets import IconValidationError, store_icon, validate_icon


def png(width: int = 32, height: int = 32) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x06\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


class PhaseThreeAssetTests(unittest.TestCase):
    def test_validated_icon_uses_content_addressed_atomic_storage(self) -> None:
        data = png()
        digest = sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = store_icon(
                data,
                declared_mime="image/png",
                source_url="https://example.com/favicon.png?token=private",
                root=root,
            )
            second = store_icon(
                data,
                declared_mime="image/png",
                source_url="https://example.com/favicon.png?token=other",
                root=root,
            )

            self.assertEqual(first.content_hash, digest)
            self.assertEqual(first.relative_path, f"{digest[:2]}/{digest[2:4]}/{digest}.png")
            self.assertTrue((root / first.relative_path).is_file())
            self.assertTrue(first.created)
            self.assertFalse(second.created)
            self.assertNotIn("token", repr(first))

    def test_fake_mime_oversize_svg_and_image_bomb_are_rejected(self) -> None:
        cases = (
            (png(), "image/jpeg", 1024, 1_000_000, "mime_mismatch"),
            (png(), "image/png", 8, 1_000_000, "image_too_large"),
            (png(100_000, 100_000), "image/png", 1024, 1_000_000, "image_dimensions"),
            (b"<svg><script>alert(1)</script></svg>", "image/svg+xml", 1024, 1_000_000, "unsupported_image_type"),
        )
        for data, mime, max_bytes, max_pixels, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(IconValidationError) as caught:
                    validate_icon(
                        data,
                        declared_mime=mime,
                        max_bytes=max_bytes,
                        max_pixels=max_pixels,
                    )
                self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main()
