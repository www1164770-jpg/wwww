# Task 4 Evidence Report — Local Background Storage Service

## Scope

Implemented only the Task 4 storage service and its focused tests:

- `backend/background_storage.py`
- `tests/test_background_storage.py`

No Task 5+ behavior was implemented. The report itself is operational evidence and is not included in the Task 4 commit.

## TDD RED

Before production code existed, ran:

```powershell
backend\venv\Scripts\python.exe -m unittest tests.test_background_storage -v
```

Result: exit code 1, one import error. The test module failed specifically because `backend.background_storage` did not exist:

```text
ModuleNotFoundError: No module named 'backend.background_storage'
Ran 1 test in 0.001s
FAILED (errors=1)
```

## GREEN

Implemented a filesystem-only module that validates `ProcessedBackground` before filesystem access, stores supplied WebP bytes atomically via a same-directory temporary path, returns a slash-normalized relative path, validates resolution below the configured root, and provides safe read/delete error normalization.

The focused suite was then run:

```powershell
backend\venv\Scripts\python.exe -m unittest tests.test_background_storage -v
```

Result: exit code 0; 9 tests passed.

During self-review, added coverage for rejecting non-byte content and boolean metadata before root creation. This assertion failed before the validator was tightened, then passed after the minimal fix.

## Final verification

Commands run after the final change:

```powershell
backend\venv\Scripts\python.exe -m unittest tests.test_background_storage -v
backend\venv\Scripts\python.exe -m py_compile backend/background_storage.py
backend\venv\Scripts\python.exe -m unittest tests.test_background_image_service tests.test_background_storage tests.test_background_storage_config tests.test_backend_startup_safety -v
git diff --check
```

Results:

- Focused storage suite: 9 tests passed.
- `py_compile`: exit code 0.
- Required regression suite: 40 tests passed, exit code 0.
- `git diff --check`: no output, exit code 0.

The regression command emitted expected application startup/Redis fallback logging but no test failures or warnings from the new storage module.

## Test coverage

The focused tests cover:

- UUID-named WebP write, relative returned path, read, and delete.
- Positive-user directory isolation.
- Invalid user/processed contracts with no root creation.
- Absolute, traversal, and out-of-root path rejection.
- Missing read versus idempotent missing delete.
- Simulated write, replace, read, and delete filesystem errors; temporary-file cleanup.
- Source-level prohibition of image decoding/processing and Pillow imports.

## Diff and commit scope

Before staging, `git diff --check` was clean and the intended implementation diff contained only the two Task 4 files above. Only those files are staged and committed. This report remains untracked and outside the commit by design.

## Self-review

- No Pillow, transformation, Flask/HTTP, database, or configuration imports/access were added.
- Storage creates only the target positive user directory when saving.
- Filesystem-facing errors expose fixed messages rather than absolute paths.
- Temporary and final target files are cleanup candidates after write/replace failure.
- No Task 5+ routes, model, migration, or configuration changes were made.

## Commit

Commit message: `feat(background): add private background storage`

Commit SHA: `f68f8cfbf995aa7fddae4c727563d046f95e4d9e`

---

## Review-fix evidence

### Scope

This follow-up changes only `backend/background_storage.py` and
`tests/test_background_storage.py`. It does not add Task 5+ behavior.

### RED

Added focused tests before modifying storage production code, then ran:

```powershell
backend\venv\Scripts\python.exe -m unittest tests.test_background_storage -v
```

Result: exit code 1; 13 tests ran with three failures and two errors:

- `.` and `C:relative.webp` were accepted instead of raising `InvalidStoragePath`.
- Cleanup `unlink` failures were silently hidden behind `Unable to store background file` instead of a stable cleanup error.
- A `FileNotFoundError` from delete after existence inspection was wrapped instead of returning `False`.
- Native temporary-directory symlink creation could not run under the local Windows token (`WinError 1314`), so the test was changed before implementation to deterministically simulate a database symlink whose resolved destination lies outside the temporary root. That test verifies the same `Path.resolve` safety boundary without requiring external files or unavailable privileges.

### GREEN

Minimal implementation changes:

- Reject root/self candidates and any drive-qualified path.
- Retain cleanup attempts for both temporary and final candidates; surface a fixed `BackgroundStorageError` if any cleanup unlink fails.
- Treat `FileNotFoundError` during delete as an idempotent `False` result.
- Preserve existing resolved-path containment rejection, including externally resolved symlink destinations.

Focused command result after the fixes: exit code 0; 13 tests passed.

### Final verification

Commands run after the final change:

```powershell
backend\venv\Scripts\python.exe -m unittest tests.test_background_storage -v
backend\venv\Scripts\python.exe -m py_compile backend/background_storage.py
backend\venv\Scripts\python.exe -m unittest tests.test_background_image_service tests.test_background_storage tests.test_background_storage_config tests.test_backend_startup_safety -v
git diff --check
```

Results:

- Focused storage suite: 13 passed.
- Compile: exit code 0.
- Required regression suite: 44 passed, exit code 0.
- `git diff --check`: exit code 0 with no output.

### Commit scope and self-review

Only the two permitted Task 4 implementation/test files are staged for the follow-up commit. The report remains operational evidence outside that commit. Messages are stable and do not contain upload-root absolute paths. No configuration, routes, models, database, image-processing, or Task 5+ code was changed.

---

## Final delete race follow-up

### RED

Added `test_delete_returns_false_when_file_disappears_before_is_file` before production changes. It simulates a safe file that exists during the first `exists()` check, returns false at `is_file()`, and is absent on the follow-up existence check. The focused command exited 1: the current code raised `BackgroundStorageError: Unable to delete background file`, proving the race was not treated idempotently.

### GREEN and verification

The minimal delete-path change rechecks existence only after `is_file()` is false, returning `False` for the disappearance race while retaining `BackgroundStorageError` for a genuinely present non-regular path or other filesystem errors.

Commands run after the change:

```powershell
backend\venv\Scripts\python.exe -m unittest tests.test_background_storage -v
backend\venv\Scripts\python.exe -m py_compile backend/background_storage.py
backend\venv\Scripts\python.exe -m unittest tests.test_background_image_service tests.test_background_storage tests.test_background_storage_config tests.test_backend_startup_safety -v
git diff --check
```

Results: focused suite 14 passed; compile exit code 0; required regression suite 45 passed; diff check is clean. Only Task 4 service/test files are modified (plus this untracked operational report). No Git commit was retried because the previous escalation was denied.
