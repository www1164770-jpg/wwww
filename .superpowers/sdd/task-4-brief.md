# Task 4 — Local Background Storage Service

Implement only Task 4 from the revised plan on `main`, currently at `93f5a37`.

## Allowed files

- Create `backend/background_storage.py`
- Create `tests/test_background_storage.py`

Do not edit any other file, especially Task 3 files, `background_config.py`, requirements, app/wsgi/routes/models/migrations, tests other than the Task 4 test, frontend, database, or `.env`.

## Required public interface

```python
from pathlib import Path

from backend.background_image_service import ProcessedBackground


def store_processed_background(
    processed: ProcessedBackground,
    user_id: int,
    upload_root: Path,
) -> str:
    ...


def resolve_background_path(upload_root: Path, storage_path: str) -> Path:
    ...


def read_background_file(upload_root: Path, storage_path: str) -> bytes:
    ...


def delete_background_file(upload_root: Path, storage_path: str) -> bool:
    ...
```

Define `InvalidStoragePath`, `BackgroundFileNotFound`, and `BackgroundStorageError`. The module consumes Task 3 `ProcessedBackground` and a positive integer user id. The caller supplies the already-configured upload root; do not import or recreate configuration values.

## Required behavior

- `store_processed_background` verifies the input contract: positive integer user id (not bool), a `ProcessedBackground`, nonempty byte content, positive dimensions/file size, fixed `image/webp` MIME, and `file_size == len(content)`. Reject invalid input before filesystem side effects.
- It creates only `<upload_root>/<user_id>/` when saving, generates a random UUID `.webp` filename, writes the supplied bytes through a same-directory temporary file, atomically replaces the final path, and returns a slash-normalized path relative to the root only. No final or temporary file may remain when a write/replace failure occurs.
- `resolve_background_path` accepts only a nonempty relative database path that resolves beneath the supplied root; reject absolute paths, `..` traversal, and any candidate outside root with `InvalidStoragePath`.
- `read_background_file` resolves safely, returns bytes, raises `BackgroundFileNotFound` if the safe path does not exist, and wraps other filesystem errors as `BackgroundStorageError` without exposing absolute paths.
- `delete_background_file` resolves safely, returns `True` when it deletes a regular file, returns `False` when a safe file is already absent, and wraps other filesystem errors as `BackgroundStorageError` without exposing absolute paths.
- This module must not import Pillow, decode/transform images, use Flask/HTTP objects, or access database data.

## Required TDD evidence and tests

Before production code, create `tests/test_background_storage.py` and run:

```powershell
backend\venv\Scripts\python.exe -m unittest tests.test_background_storage -v
```

It must fail because `backend.background_storage` is missing. Record this RED output in the report.

Use temporary roots. Cover successful UUID WebP storage/read/delete and returned relative path; directory isolation for positive user id; invalid processed input without root creation; absolute/traversal/out-of-root path rejection; missing read versus idempotent missing delete; simulated write/replace/read/delete errors and temporary-file cleanup; source-level no Pillow/image processing. Do not add tests outside this file.

After minimal implementation, run focused test, `backend\venv\Scripts\python.exe -m py_compile backend/background_storage.py`, and:

```powershell
backend\venv\Scripts\python.exe -m unittest tests.test_background_image_service tests.test_background_storage tests.test_background_storage_config tests.test_backend_startup_safety -v
```

Run `git diff --check` and confirm only the two files are changed. Commit only those files as:

```text
feat(background): add private background storage
```

## Report

Write full RED/GREEN/test/diff/scope/commit/self-review evidence to `.superpowers/sdd/task-4-report.md`. Return only status, SHA, test summary, and concerns.
