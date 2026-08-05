"""Dependency-free image header validation and atomic icon storage."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import struct
import tempfile

from backend.crawler.net.url import safe_url_for_output


class IconValidationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ValidatedIcon:
    content_hash: str
    mime_type: str
    extension: str
    width: int
    height: int
    byte_size: int


@dataclass(frozen=True, slots=True)
class StoredIcon:
    content_hash: str
    mime_type: str
    width: int
    height: int
    byte_size: int
    relative_path: str
    source_url: str
    created: bool


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    offset = 2
    while offset + 9 <= len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            break
        length = struct.unpack(">H", data[offset : offset + 2])[0]
        if length < 2 or offset + length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            return width, height
        offset += length
    raise IconValidationError("invalid_image")


def _image_type(data: bytes) -> tuple[str, str, int, int]:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24 and data[12:16] == b"IHDR":
        width, height = struct.unpack(">II", data[16:24])
        return "image/png", "png", width, height
    if data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
        return "image/gif", "gif", width, height
    if data.startswith(b"\xff\xd8"):
        width, height = _jpeg_dimensions(data)
        return "image/jpeg", "jpg", width, height
    if data.startswith(b"RIFF") and len(data) >= 30 and data[8:12] == b"WEBP" and data[12:16] == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return "image/webp", "webp", width, height
    if data.startswith(b"\x00\x00\x01\x00") and len(data) >= 8:
        width = data[6] or 256
        height = data[7] or 256
        return "image/x-icon", "ico", width, height
    raise IconValidationError("unsupported_image_type")


def validate_icon(
    data: bytes,
    *,
    declared_mime: str,
    max_bytes: int = 1_048_576,
    max_pixels: int = 16_777_216,
) -> ValidatedIcon:
    if not isinstance(data, bytes) or not data:
        raise IconValidationError("invalid_image")
    if max_bytes < 1 or len(data) > max_bytes:
        raise IconValidationError("image_too_large")
    actual_mime, extension, width, height = _image_type(data)
    declared = declared_mime.partition(";")[0].strip().lower()
    aliases = {"image/vnd.microsoft.icon": "image/x-icon"}
    declared = aliases.get(declared, declared)
    if declared != actual_mime:
        raise IconValidationError("mime_mismatch")
    if width < 1 or height < 1 or width > 16_384 or height > 16_384 or width * height > max_pixels:
        raise IconValidationError("image_dimensions")
    return ValidatedIcon(
        content_hash=sha256(data).hexdigest(),
        mime_type=actual_mime,
        extension=extension,
        width=width,
        height=height,
        byte_size=len(data),
    )


def store_icon(
    data: bytes,
    *,
    declared_mime: str,
    source_url: str,
    root: Path,
    max_bytes: int = 1_048_576,
    max_pixels: int = 16_777_216,
) -> StoredIcon:
    validated = validate_icon(
        data,
        declared_mime=declared_mime,
        max_bytes=max_bytes,
        max_pixels=max_pixels,
    )
    resolved_root = Path(root).resolve()
    relative = Path(validated.content_hash[:2]) / validated.content_hash[2:4] / (
        f"{validated.content_hash}.{validated.extension}"
    )
    destination = (resolved_root / relative).resolve()
    try:
        destination.relative_to(resolved_root)
    except ValueError as error:
        raise IconValidationError("unsafe_storage_path") from error
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = not destination.exists()
    if created:
        handle, temporary_name = tempfile.mkstemp(prefix=".icon-", dir=destination.parent)
        try:
            with os.fdopen(handle, "wb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_name, destination)
        except BaseException:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise
    return StoredIcon(
        content_hash=validated.content_hash,
        mime_type=validated.mime_type,
        width=validated.width,
        height=validated.height,
        byte_size=validated.byte_size,
        relative_path=relative.as_posix(),
        source_url=safe_url_for_output(source_url),
        created=created,
    )
