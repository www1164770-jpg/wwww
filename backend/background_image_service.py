"""In-memory processing for private background-image uploads."""

import io
import warnings
from dataclasses import dataclass
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from .background_config import (
    BACKGROUND_ALLOWED_IMAGE_FORMATS,
    BACKGROUND_MAX_FILE_BYTES,
    BACKGROUND_MAX_HEIGHT,
    BACKGROUND_MAX_PIXELS,
    BACKGROUND_MAX_WIDTH,
    BACKGROUND_OUTPUT_FORMAT,
    BACKGROUND_OUTPUT_MIME_TYPE,
    BACKGROUND_WEBP_QUALITY,
)
from .background_analysis import analyze_background


class BackgroundUploadTooLarge(ValueError):
    """Raised when an upload exceeds the configured source-byte limit."""


class InvalidBackgroundImage(ValueError):
    """Raised when an upload cannot be safely processed as a background image."""

    def __init__(self, message: str, error_code: str = "UPLOAD_PIL_FAILED"):
        super().__init__(message)
        self.error_code = error_code


class BackgroundImageAnalysisError(RuntimeError):
    """Raised when a valid transcoded image cannot be analyzed."""


@dataclass(frozen=True)
class ProcessedBackground:
    content: bytes
    width: int
    height: int
    mime_type: str
    file_size: int
    analysis: dict | None = None


def _read_limited(file_stream: BinaryIO) -> bytes:
    content = bytearray()
    while len(content) <= BACKGROUND_MAX_FILE_BYTES:
        remaining = BACKGROUND_MAX_FILE_BYTES + 1 - len(content)
        chunk = file_stream.read(remaining)
        if not chunk:
            return bytes(content)
        if len(chunk) > remaining:
            raise BackgroundUploadTooLarge("Background upload exceeds the maximum file size")
        content.extend(chunk)
    raise BackgroundUploadTooLarge("Background upload exceeds the maximum file size")


def _is_alpha_image(image: Image.Image) -> bool:
    return "A" in image.getbands() or "transparency" in image.info


def process_background_upload(
    file_stream: BinaryIO,
    original_filename: str,
    content_length: int | None = None,
) -> ProcessedBackground:
    """Validate, normalize, and transcode a source upload entirely in memory."""
    del original_filename

    if content_length is not None and content_length > BACKGROUND_MAX_FILE_BYTES:
        raise BackgroundUploadTooLarge("Background upload exceeds the maximum file size")

    try:
        source = _read_limited(file_stream)
    except BackgroundUploadTooLarge:
        raise
    except OSError as error:
        raise InvalidBackgroundImage("Invalid background image") from error
    if not source:
        raise InvalidBackgroundImage("Background upload is empty", "UPLOAD_FILE_EMPTY")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(source)) as verified_image:
                if verified_image.format not in BACKGROUND_ALLOWED_IMAGE_FORMATS:
                    raise InvalidBackgroundImage("Unsupported background image format", "UPLOAD_FORMAT_INVALID")
                verified_image.verify()

            with Image.open(io.BytesIO(source)) as source_image:
                if getattr(source_image, "is_animated", False) or getattr(source_image, "n_frames", 1) != 1:
                    raise InvalidBackgroundImage("Animated background images are not allowed", "UPLOAD_FORMAT_INVALID")
                if source_image.width * source_image.height > BACKGROUND_MAX_PIXELS:
                    raise InvalidBackgroundImage("Background image exceeds the pixel limit", "UPLOAD_DIMENSIONS_INVALID")
                image = ImageOps.exif_transpose(source_image)
                image = image.convert("RGBA" if _is_alpha_image(image) else "RGB")
                image.thumbnail(
                    (BACKGROUND_MAX_WIDTH, BACKGROUND_MAX_HEIGHT),
                    Image.Resampling.LANCZOS,
                )
                output = io.BytesIO()
                image.save(
                    output,
                    format=BACKGROUND_OUTPUT_FORMAT,
                    quality=BACKGROUND_WEBP_QUALITY,
                    method=6,
                )
    except (Image.DecompressionBombWarning, Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        if isinstance(error, InvalidBackgroundImage):
            raise
        raise InvalidBackgroundImage("Invalid background image") from error

    content = output.getvalue()
    try:
        analysis = analyze_background(content)
    except Exception as error:
        raise BackgroundImageAnalysisError("Unable to analyze processed background") from error

    return ProcessedBackground(
        content=content,
        width=image.width,
        height=image.height,
        mime_type=BACKGROUND_OUTPUT_MIME_TYPE,
        file_size=len(content),
        analysis=analysis,
    )
