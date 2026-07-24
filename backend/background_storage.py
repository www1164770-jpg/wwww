"""Private filesystem storage for already-processed background files."""

import os
from pathlib import Path
from uuid import uuid4

from backend.background_image_service import ProcessedBackground


class InvalidStoragePath(ValueError):
    """Raised when a database storage path is unsafe."""


class BackgroundFileNotFound(FileNotFoundError):
    """Raised when a safely resolved background file is absent."""


class BackgroundStorageError(RuntimeError):
    """Raised when a filesystem operation cannot be completed."""


def _validate_processed_background(processed: ProcessedBackground, user_id: int) -> None:
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    if not isinstance(processed, ProcessedBackground):
        raise ValueError("processed must be a ProcessedBackground")
    if (
        not isinstance(processed.content, bytes)
        or not processed.content
        or isinstance(processed.width, bool)
        or not isinstance(processed.width, int)
        or processed.width <= 0
        or isinstance(processed.height, bool)
        or not isinstance(processed.height, int)
        or processed.height <= 0
        or isinstance(processed.file_size, bool)
        or not isinstance(processed.file_size, int)
        or processed.file_size <= 0
        or processed.mime_type != "image/webp"
        or processed.file_size != len(processed.content)
    ):
        raise ValueError("processed background is invalid")


def store_processed_background(
    processed: ProcessedBackground,
    user_id: int,
    upload_root: Path,
) -> str:
    """Atomically save processed content and return its root-relative path."""
    _validate_processed_background(processed, user_id)

    user_directory = Path(upload_root) / str(user_id)
    filename = f"{uuid4()}.webp"
    final_path = user_directory / filename
    temporary_path = user_directory / f".{filename}.{uuid4().hex}.tmp"
    try:
        user_directory.mkdir(parents=True, exist_ok=True)
        temporary_path.write_bytes(processed.content)
        os.replace(temporary_path, final_path)
    except OSError as error:
        for path in (temporary_path, final_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise BackgroundStorageError("Unable to store background file") from error

    return f"{user_id}/{filename}"


def resolve_background_path(upload_root: Path, storage_path: str) -> Path:
    """Resolve a database path only when it stays below the configured root."""
    if not isinstance(storage_path, str) or not storage_path.strip():
        raise InvalidStoragePath("Storage path must be a nonempty relative path")

    path = Path(storage_path)
    if path.is_absolute() or ".." in path.parts:
        raise InvalidStoragePath("Storage path is invalid")

    root = Path(upload_root).resolve()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise InvalidStoragePath("Storage path is invalid") from error
    return candidate


def read_background_file(upload_root: Path, storage_path: str) -> bytes:
    """Read a safely resolved private background file."""
    path = resolve_background_path(upload_root, storage_path)
    try:
        return path.read_bytes()
    except FileNotFoundError as error:
        raise BackgroundFileNotFound("Background file was not found") from error
    except OSError as error:
        raise BackgroundStorageError("Unable to read background file") from error


def delete_background_file(upload_root: Path, storage_path: str) -> bool:
    """Delete a safely resolved private background file when it exists."""
    path = resolve_background_path(upload_root, storage_path)
    try:
        if not path.exists():
            return False
        if not path.is_file():
            raise OSError("Background path is not a regular file")
        path.unlink()
        return True
    except OSError as error:
        raise BackgroundStorageError("Unable to delete background file") from error
