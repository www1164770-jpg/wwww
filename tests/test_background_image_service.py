import io
import struct
import unittest
import zlib
from unittest.mock import patch

from PIL import Image

from backend.background_image_service import (
    BackgroundUploadTooLarge,
    InvalidBackgroundImage,
    ProcessedBackground,
    process_background_upload,
)
from backend.background_config import (
    BACKGROUND_MAX_FILE_BYTES,
    BACKGROUND_MAX_HEIGHT,
    BACKGROUND_MAX_PIXELS,
    BACKGROUND_MAX_WIDTH,
    BACKGROUND_OUTPUT_MIME_TYPE,
)


def image_bytes(image, image_format, **save_options):
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **save_options)
    return buffer.getvalue()


class OversizeStream:
    def __init__(self, total_size):
        self.remaining = total_size

    def read(self, size=-1):
        if self.remaining <= 0:
            return b""
        count = self.remaining if size < 0 else min(size, self.remaining)
        self.remaining -= count
        return b"x" * count


class OversizedChunkStream:
    def read(self, size=-1):
        return b"x" * (size + 1)


class BoundedByteArray(bytearray):
    def extend(self, value):
        if len(self) + len(value) > BACKGROUND_MAX_FILE_BYTES + 1:
            raise AssertionError("source buffer exceeded the configured bound")
        super().extend(value)


def png_header(width, height):
    def chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IEND", b"")
    )


class BackgroundImageServiceTests(unittest.TestCase):
    def test_processes_jpeg_to_webp_without_upscaling(self):
        source = image_bytes(Image.new("RGB", (120, 80), "red"), "JPEG")

        result = process_background_upload(io.BytesIO(source), "portrait.jpg")

        self.assertEqual((result.width, result.height), (120, 80))
        self.assertEqual(result.mime_type, BACKGROUND_OUTPUT_MIME_TYPE)
        self.assertEqual(result.file_size, len(result.content))
        with Image.open(io.BytesIO(result.content)) as output:
            self.assertEqual(output.format, "WEBP")
            self.assertEqual(output.mode, "RGB")

    def test_downscales_large_jpeg_proportionally(self):
        source = image_bytes(Image.new("RGB", (4000, 2000), "blue"), "JPEG")

        result = process_background_upload(io.BytesIO(source), "wide.jpg")

        self.assertEqual((result.width, result.height), (BACKGROUND_MAX_WIDTH, 1280))
        self.assertLessEqual(result.width, BACKGROUND_MAX_WIDTH)
        self.assertLessEqual(result.height, BACKGROUND_MAX_HEIGHT)

    def test_preserves_png_alpha_as_rgba(self):
        source = image_bytes(Image.new("RGBA", (80, 50), (10, 20, 30, 100)), "PNG")

        result = process_background_upload(io.BytesIO(source), "alpha.png")

        with Image.open(io.BytesIO(result.content)) as output:
            self.assertEqual(output.mode, "RGBA")
            self.assertEqual(output.getpixel((0, 0))[3], 100)

    def test_accepts_static_webp(self):
        source = image_bytes(Image.new("RGB", (64, 48), "green"), "WEBP")

        result = process_background_upload(io.BytesIO(source), "already.webp")

        self.assertEqual((result.width, result.height), (64, 48))
        self.assertEqual(result.mime_type, "image/webp")

    def test_rejects_animated_webp(self):
        first = Image.new("RGB", (20, 20), "red")
        second = Image.new("RGB", (20, 20), "blue")
        source = image_bytes(first, "WEBP", save_all=True, append_images=[second], duration=100, loop=0)

        with self.assertRaises(InvalidBackgroundImage):
            process_background_upload(io.BytesIO(source), "animated.webp")

    def test_rejects_invalid_bytes_and_unsupported_format(self):
        with self.assertRaises(InvalidBackgroundImage):
            process_background_upload(io.BytesIO(b"not an image"), "bad.bin")

        gif = image_bytes(Image.new("RGB", (8, 8), "white"), "GIF")
        with self.assertRaises(InvalidBackgroundImage):
            process_background_upload(io.BytesIO(gif), "unsupported.gif")

    def test_rejects_empty_input(self):
        with self.assertRaises(InvalidBackgroundImage):
            process_background_upload(io.BytesIO(), "empty.png")

    def test_applies_exif_orientation(self):
        image = Image.new("RGB", (40, 80), "purple")
        exif = Image.Exif()
        exif[274] = 6
        source = image_bytes(image, "JPEG", exif=exif)

        result = process_background_upload(io.BytesIO(source), "rotated.jpg")

        self.assertEqual((result.width, result.height), (80, 40))

    def test_strips_input_metadata(self):
        image = Image.new("RGB", (20, 20), "orange")
        exif = Image.Exif()
        exif[270] = "private title"
        source = image_bytes(image, "JPEG", exif=exif, icc_profile=b"not-a-real-profile")

        result = process_background_upload(io.BytesIO(source), "metadata.jpg")

        with Image.open(io.BytesIO(result.content)) as output:
            self.assertNotIn("exif", output.info)
            self.assertNotIn("icc_profile", output.info)
            self.assertNotIn("xmp", output.info)

    def test_rejects_declared_content_length_above_limit(self):
        with self.assertRaises(BackgroundUploadTooLarge):
            process_background_upload(
                io.BytesIO(b"small"), "declared.png", content_length=BACKGROUND_MAX_FILE_BYTES + 1
            )

    def test_rejects_observed_stream_above_limit(self):
        with self.assertRaises(BackgroundUploadTooLarge):
            process_background_upload(OversizeStream(BACKGROUND_MAX_FILE_BYTES + 1), "large.png")

    def test_caps_buffer_when_stream_returns_more_than_requested(self):
        with patch("builtins.bytearray", BoundedByteArray):
            with self.assertRaises(BackgroundUploadTooLarge):
                process_background_upload(OversizedChunkStream(), "untrusted.png")

    def test_converts_exact_over_pixel_limit_decompression_warning(self):
        source = png_header(1, BACKGROUND_MAX_PIXELS + 1)

        with patch.object(Image, "MAX_IMAGE_PIXELS", BACKGROUND_MAX_PIXELS):
            with self.assertRaises(InvalidBackgroundImage):
                process_background_upload(io.BytesIO(source), "warning.png")

    def test_rejects_image_above_pixel_limit(self):
        side = int(BACKGROUND_MAX_PIXELS ** 0.5) + 1
        source = image_bytes(Image.new("RGB", (side, side), "black"), "PNG")

        with self.assertRaises(InvalidBackgroundImage):
            process_background_upload(io.BytesIO(source), "huge.png")

    def test_processed_background_is_frozen(self):
        result = ProcessedBackground(b"data", 1, 1, "image/webp", 4)

        with self.assertRaisesRegex(Exception, "cannot assign to field"):
            result.width = 2


if __name__ == "__main__":
    unittest.main()
