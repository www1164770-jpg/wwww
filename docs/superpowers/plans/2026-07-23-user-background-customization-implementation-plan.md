# User Background Customization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each authenticated account a private background library and per-page background configuration, including overlay, blur, position, and scale.

**Architecture:** Flask V1 routes use the existing PyMySQL connection pool for two MySQL tables and protected local WebP files. A Pinia background store owns metadata, settings, Blob URLs, and drafts; one fixed background component renders the page while the AI panel reuses the same effective setting.

**Tech Stack:** Flask, PyMySQL, SQLAlchemy, MySQL 8.0.45, Pillow, Vue 3, Pinia, Vue Router, Axios, Node.js static verification scripts.

## Global Constraints

- At most 10 `active` background images per user; each source upload is at most 10 MiB.
- Accept only JPEG, PNG, and WebP verified by Pillow; write WebP at quality 84, maximum 2560x1440 and 20,000,000 pixels.
- Page types are exactly `global`, `home`, `category`, `favorites`, `ai_assistant`, and `profile`.
- All image reads are private JWT requests; never expose an uploads URL, client-selected path, absolute path, original filename, token, or image contents in logs.
- Store only server-generated relative paths; do not commit local uploads and add no public static route for them.
- Do not change Authing configuration or rewrite authentication. Preserve favorites, search, career recommendation, and AI recommendation behavior.
- Local storage requires a writable backed-up volume. Vercel/serverless local disks are not persistent; use an object-storage adapter before such a deployment.
- Keep `users.custom_wallpaper` read-only audit data for one release cycle; the new feature neither reads nor writes it.
- Every implementation task starts with a failing test, verifies failure, makes the smallest change, runs focused and regression checks, inspects only task files, and commits without pushing.

## Planned File Structure

| Path | Responsibility |
| --- | --- |
| `backend/sql/migrations/20260723_user_backgrounds.up.sql` | Two MySQL tables, keys, checks, and foreign keys. |
| `backend/background_service.py` | Path validation, Pillow processing, private metadata projection, and secure deletion helpers. |
| `backend/background_migration.py` | One-shot controlled migration of valid legacy HTTPS wallpaper URLs. |
| `backend/v1_routes.py` | Private library and setting API endpoints only. |
| `backend/app.py`, `backend/models.py`, `requirements.txt`, `.gitignore` | Configuration, model declarations, Pillow pin, and ignored upload root. |
| `tests/test_background_*.py` | `unittest` coverage of schema, image processing, V1 API, settings, and migration. |
| `backend/frontend/src/utils/background.js` | Pure page-type, defaults, validation, and inheritance functions. |
| `backend/frontend/src/stores/background.js` | Session-owned library, settings, Blob cache, drafts, and cleanup. |
| `backend/frontend/src/components/background/*.vue` | Global layer, modal, library, and preview responsibilities. |
| `backend/frontend/scripts/verify-background-*.mjs` | Existing-style source assertions and lifecycle checks. |

---

## Phase 1: Database and Private Background Library Backend

### Task 1: Background schema and SQLAlchemy boundary

**Files:**
- Create: `backend/sql/migrations/20260723_user_backgrounds.up.sql`, `tests/test_background_schema.py`
- Modify: `backend/models.py`
- Test: `tests/test_background_schema.py`

**Interfaces:**
- Consumes: `users.id` and the existing `backend/sql/migrations` naming convention.
- Produces: `UserBackground`, `UserBackgroundSetting`, and DDL for `user_backgrounds` and `user_background_settings`.

- [ ] **Step 1: Write the failing test.** Assert the migration contains `UNIQUE KEY uq_user_background_settings_page (user_id, page_type)`, the six-value enum, `ON DELETE SET NULL`, and SQLAlchemy fields `storage_path`, `background_id`, and `overlay_opacity`.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_schema -v`; expect `FAIL` because the migration and models do not exist.
- [ ] **Step 3: Write the minimal implementation.** Add the two design-approved `CREATE TABLE` statements, including `status ENUM('active','deleted')`, all checks, indexes, and FKs. Add models with `db.ForeignKey("users.id", ondelete="CASCADE")`, `db.ForeignKey("user_backgrounds.id", ondelete="SET NULL")`, and matching defaults.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_schema -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_db_startup tests.test_backend_startup_safety -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/sql/migrations/20260723_user_backgrounds.up.sql backend/models.py tests/test_background_schema.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/sql/migrations/20260723_user_backgrounds.up.sql backend/models.py tests/test_background_schema.py` then `git commit -m "feat(background): add background schema"`.

### Task 2: Storage configuration and ignored private root

**Files:**
- Create: `tests/test_background_storage_config.py`
- Modify: `backend/app.py`, `.gitignore`
- Test: `tests/test_background_storage_config.py`

**Interfaces:**
- Consumes: Flask `app.config` and `Path(__file__).resolve().parent`.
- Produces: `BACKGROUND_UPLOAD_ROOT` resolving to `backend/uploads` when no environment override exists.

- [ ] **Step 1: Write the failing test.** Load `backend/app.py` source and assert `BACKGROUND_UPLOAD_ROOT`, `Path`, and `app.config.setdefault` appear; assert `.gitignore` contains exactly `backend/uploads/`.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_storage_config -v`; expect `FAIL` on missing configuration.
- [ ] **Step 3: Write the minimal implementation.** In application configuration set `app.config["BACKGROUND_UPLOAD_ROOT"] = os.environ.get("BACKGROUND_UPLOAD_ROOT", str(Path(__file__).resolve().parent / "uploads"))`; do not create the directory at startup. Add `backend/uploads/` to `.gitignore`.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_storage_config -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_backend_runtime_config tests.test_backend_startup_safety -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/app.py .gitignore tests/test_background_storage_config.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/app.py .gitignore tests/test_background_storage_config.py` then `git commit -m "feat(background): configure private upload storage"`.

### Task 3: Pillow validation and WebP processing service

**Files:**
- Create: `backend/background_service.py`, `tests/test_background_image_processing.py`
- Modify: `requirements.txt`
- Test: `tests/test_background_image_processing.py`

**Interfaces:**
- Consumes: `FileStorage.stream`, configured upload root, and bytes limited to 10,485,760.
- Produces: `process_background_upload(file_storage, user_id, upload_root) -> dict` with `relative_path`, `mime_type`, `file_size`, `width`, and `height`.

- [ ] **Step 1: Write the failing test.** Use generated in-memory JPEG, PNG with alpha, WebP, GIF, invalid bytes, and a mocked 20,000,001-pixel image. Assert JPEG becomes `image/webp`, output quality is invoked as `84`, width and height do not exceed 2560/1440, and invalid types raise `InvalidBackgroundImage`.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_image_processing -v`; expect import failure for `background_service`.
- [ ] **Step 3: Write the minimal implementation.** Pin `Pillow>=10.0.0,<12.0.0`. Define `MAX_UPLOAD_BYTES = 10_485_760`, `MAX_IMAGE_PIXELS = 20_000_000`, and `process_background_upload`. Call `Image.verify()`, reopen, convert `DecompressionBombWarning` into `InvalidBackgroundImage`, apply `ImageOps.exif_transpose`, `thumbnail((2560,1440), Image.Resampling.LANCZOS)`, convert RGB/RGBA, and atomically replace a UUID `.webp` from `.tmp`.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_image_processing -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m py_compile backend/background_service.py` and `python -m unittest tests.test_backend_startup_safety -v`; expect no compile error and `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/background_service.py requirements.txt tests/test_background_image_processing.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/background_service.py requirements.txt tests/test_background_image_processing.py` then `git commit -m "feat(background): process private background images"`.

### Task 4: Atomic file cleanup helpers

**Files:**
- Create: `tests/test_background_file_cleanup.py`
- Modify: `backend/background_service.py`
- Test: `tests/test_background_file_cleanup.py`

**Interfaces:**
- Consumes: `relative_path` from Task 3 and the configured root.
- Produces: `resolve_background_path(root, relative_path) -> Path` and `delete_background_file(root, relative_path) -> bool`.

- [ ] **Step 1: Write the failing test.** Assert `backgrounds/42/a.webp` resolves below the root, `../escape.webp` and absolute paths raise `InvalidStoragePath`, and a missing file returns `False` without creating directories.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_file_cleanup -v`; expect missing helper failures.
- [ ] **Step 3: Write the minimal implementation.** Resolve both root and candidate, reject `candidate` unless `candidate.is_relative_to(root)`, and unlink only the resolved candidate. In `process_background_upload`, remove the temporary file on every exception and remove the final file when its caller reports database failure.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_file_cleanup -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_background_image_processing tests.test_background_file_cleanup -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/background_service.py tests/test_background_file_cleanup.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/background_service.py tests/test_background_file_cleanup.py` then `git commit -m "feat(background): secure private file cleanup"`.

### Task 5: Private background library read endpoint

**Files:**
- Create: `tests/test_background_library_v1.py`
- Modify: `backend/v1_routes.py`
- Test: `tests/test_background_library_v1.py`

**Interfaces:**
- Consumes: `current_user_row()`, `get_db_connection()`, and `api_success()` inside `register_v1_routes`.
- Produces: `GET /api/backgrounds -> {data:{items:[{id,original_name,mime_type,file_size,width,height,created_at}]}}`.

- [ ] **Step 1: Write the failing test.** Mock the V1 connection and JWT identity; assert the query includes `user_id=%s AND status='active'`, output has no `storage_path`, and absent user returns the V1 401 body.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_library_v1 -v`; expect route-not-found or assertion failure.
- [ ] **Step 3: Write the minimal implementation.** Add a `background_item(row)` projection helper and a JWT-protected route inside `register_v1_routes`; query ordered by `created_at DESC, id DESC`, close the connection, and return `api_success({"items": items})`.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_library_v1 -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_auth tests.test_favorites_v1 -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/v1_routes.py tests/test_background_library_v1.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/v1_routes.py tests/test_background_library_v1.py` then `git commit -m "feat(background): add private background library read API"`.

### Task 6: Upload endpoint with quota and transaction rollback

**Files:**
- Create: `tests/test_background_upload_v1.py`
- Modify: `backend/v1_routes.py`, `backend/background_service.py`
- Test: `tests/test_background_upload_v1.py`

**Interfaces:**
- Consumes: Task 3 processor and `POST /api/backgrounds` multipart field `file`.
- Produces: 201 `{background:item}`, errors 400, 409 `background_library_full`, 413, and 422 `invalid_background_image`.

- [ ] **Step 1: Write the failing test.** Cover missing file, a valid upload, ten locked active rows, an oversized content length, invalid bytes, `rollback()` after INSERT failure, and final-file removal after that rollback.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_upload_v1 -v`; expect endpoint failure.
- [ ] **Step 3: Write the minimal implementation.** Lock the current user using `SELECT id FROM users WHERE id=%s FOR UPDATE`, count active rows, call the processor only below quota, insert metadata with `%s` parameters, `commit`, and on every exception `rollback` then remove the created final relative path. Do not log source names, paths, tokens, or bytes.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_upload_v1 -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_background_library_v1 tests.test_auth -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/v1_routes.py backend/background_service.py tests/test_background_upload_v1.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/v1_routes.py backend/background_service.py tests/test_background_upload_v1.py` then `git commit -m "feat(background): add private background upload API"`.

### Task 7: Authenticated image download endpoint

**Files:**
- Create: `tests/test_background_image_read_v1.py`
- Modify: `backend/v1_routes.py`
- Test: `tests/test_background_image_read_v1.py`

**Interfaces:**
- Consumes: active image metadata selected by `id`, `user_id`, and Task 4 safe resolver.
- Produces: `GET /api/backgrounds/<int:background_id>/image` binary WebP with private cache headers.

- [ ] **Step 1: Write the failing test.** Assert owner receives `Content-Type: image/webp` and `Cache-Control: private, max-age=300, no-transform`; non-owner, deleted record, and missing file each yield 404 without a path.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_image_read_v1 -v`; expect missing endpoint failure.
- [ ] **Step 3: Write the minimal implementation.** Query `WHERE id=%s AND user_id=%s AND status='active'`, derive the file exclusively with `resolve_background_path`, use `send_file(path, mimetype="image/webp", conditional=True)`, set the private cache header, and return `api_error("background not found",404,404)` for all unavailable cases.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_image_read_v1 -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_background_library_v1 tests.test_background_upload_v1 -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/v1_routes.py tests/test_background_image_read_v1.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/v1_routes.py tests/test_background_image_read_v1.py` then `git commit -m "feat(background): add private background image API"`.

### Task 8: Idempotent deletion and reference clearing

**Files:**
- Create: `tests/test_background_delete_v1.py`
- Modify: `backend/v1_routes.py`
- Test: `tests/test_background_delete_v1.py`

**Interfaces:**
- Consumes: active/deleted library records and future `user_background_settings.background_id` references.
- Produces: `DELETE /api/backgrounds/<int:background_id> -> {background_id,deleted}`.

- [ ] **Step 1: Write the failing test.** Assert deletion locks its row, sets dependent settings `background_id=NULL`, marks active metadata deleted, deletes file only after commit, leaves deleted retry as `{deleted:false}`, and logs a disk unlink failure without restoring a database reference.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_delete_v1 -v`; expect missing endpoint failure.
- [ ] **Step 3: Write the minimal implementation.** Select the owner record with `status IN ('active','deleted') FOR UPDATE`; for active rows update settings first, then status, commit, then call `delete_background_file`. Roll back before any file deletion on database failure.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_delete_v1 -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_background_image_read_v1 tests.test_favorites_v1 -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/v1_routes.py tests/test_background_delete_v1.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/v1_routes.py tests/test_background_delete_v1.py` then `git commit -m "feat(background): add private background deletion"`.

### Task 9: Phase 1 backend acceptance

**Files:**
- Create: `tests/test_background_library_regression.py`
- Modify: `tests/test_background_library_v1.py`
- Test: `tests/test_background_library_regression.py`

**Interfaces:**
- Consumes: Tasks 1-8.
- Produces: a reproducible backend acceptance suite for library behavior only.

- [ ] **Step 1: Write the failing test.** Build one integration-style fixture proving one user cannot list, read, or delete another user's image and that failed processing leaves no `.tmp` or final file.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_library_regression -v`; expect a targeted failure until all fixtures use the finalized API.
- [ ] **Step 3: Write the minimal implementation.** Align test fixture request headers, mocked connection cursor behavior, and temporary upload root with the finalized V1 routes; production behavior is unchanged.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_library_regression -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest discover -s tests -v`; expect all tests `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- tests/test_background_library_v1.py tests/test_background_library_regression.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add tests/test_background_library_v1.py tests/test_background_library_regression.py` then `git commit -m "test(background): cover private library acceptance"`.

## Phase 2: Page Configuration and Inheritance API

### Task 10: Settings validation and effective-resolution service

**Files:**
- Create: `backend/background_settings.py`, `tests/test_background_settings_service.py`
- Test: `tests/test_background_settings_service.py`

**Interfaces:**
- Consumes: setting dictionaries from MySQL.
- Produces: `PAGE_TYPES`, `DEFAULT_BACKGROUND_SETTINGS`, `validate_setting_payload(payload)`, and `resolve_effective_setting(page, global_setting)`.

- [ ] **Step 1: Write the failing test.** Assert defaults are `0.36,0,50,50,"cover"`; only the six page types and `cover|contain|auto` pass; overlay accepts 0.00-0.70, blur 0-20, coordinates 0-100; a page `background_id=None` inherits only the global image.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_settings_service -v`; expect import failure.
- [ ] **Step 3: Write the minimal implementation.** Define frozen constants and validators that require all six PUT keys, use exact numeric ranges, and return `{background_id,overlay_opacity,blur_px,position_x,position_y,size_mode}`. Merge page parameters independently from image fallback.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_settings_service -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m py_compile backend/background_settings.py` and `python -m unittest tests.test_background_schema -v`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/background_settings.py tests/test_background_settings_service.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/background_settings.py tests/test_background_settings_service.py` then `git commit -m "feat(background): validate page settings"`.

### Task 11: Read page settings endpoint

**Files:**
- Create: `tests/test_background_settings_read_v1.py`
- Modify: `backend/v1_routes.py`
- Test: `tests/test_background_settings_read_v1.py`

**Interfaces:**
- Consumes: Task 10 constants and authenticated current user.
- Produces: `GET /api/background-settings -> {settings:{page_type:record},defaults:record}`.

- [ ] **Step 1: Write the failing test.** Assert only the requesting user's rows appear, keys are page types, values retain `background_id:null`, and invalid user identity receives V1 401.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_settings_read_v1 -v`; expect route-not-found.
- [ ] **Step 3: Write the minimal implementation.** Select the declared setting columns by `user_id=%s`, normalize each row with Task 10 defaults, and return the raw persistent map plus `DEFAULT_BACKGROUND_SETTINGS` through `api_success`.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_settings_read_v1 -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_background_library_v1 tests.test_auth -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/v1_routes.py tests/test_background_settings_read_v1.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/v1_routes.py tests/test_background_settings_read_v1.py` then `git commit -m "feat(background): read page background settings"`.

### Task 12: Idempotent setting upsert endpoint

**Files:**
- Create: `tests/test_background_settings_put_v1.py`
- Modify: `backend/v1_routes.py`
- Test: `tests/test_background_settings_put_v1.py`

**Interfaces:**
- Consumes: Task 10 validated payload and active background ownership query.
- Produces: `PUT /api/background-settings/<page_type>` with one full setting record.

- [ ] **Step 1: Write the failing test.** Cover each boundary value, malformed JSON, unknown type, missing key, owned active image, missing image 404, foreign image 409, null image, and two identical PUTs with one `UNIQUE(user_id,page_type)` row.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_settings_put_v1 -v`; expect missing endpoint failures.
- [ ] **Step 3: Write the minimal implementation.** Validate path and payload, query `user_backgrounds` with owner and active status when `background_id` is not null, then execute `INSERT ... ON DUPLICATE KEY UPDATE background_id=VALUES(background_id), overlay_opacity=VALUES(overlay_opacity), blur_px=VALUES(blur_px), position_x=VALUES(position_x), position_y=VALUES(position_y), size_mode=VALUES(size_mode)` and commit.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_settings_put_v1 -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_background_settings_service tests.test_background_delete_v1 -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/v1_routes.py tests/test_background_settings_put_v1.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/v1_routes.py tests/test_background_settings_put_v1.py` then `git commit -m "feat(background): save per-page background settings"`.

### Task 13: Idempotent setting reset endpoint

**Files:**
- Create: `tests/test_background_settings_delete_v1.py`
- Modify: `backend/v1_routes.py`
- Test: `tests/test_background_settings_delete_v1.py`

**Interfaces:**
- Consumes: authenticated owner and fixed page type validation.
- Produces: `DELETE /api/background-settings/<page_type> -> {page_type,deleted}`.

- [ ] **Step 1: Write the failing test.** Assert an existing page row returns `deleted:true`, a repeat returns `false`, bad page type returns 400, and deleting `global` leaves no persistent image or parameter fallback.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_settings_delete_v1 -v`; expect route-not-found.
- [ ] **Step 3: Write the minimal implementation.** Reject types outside `PAGE_TYPES`, delete by `user_id=%s AND page_type=%s`, capture `cursor.rowcount`, commit, and return `api_success({"page_type":page_type,"deleted":bool(rowcount)})`.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_settings_delete_v1 -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_background_settings_read_v1 tests.test_background_settings_put_v1 -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/v1_routes.py tests/test_background_settings_delete_v1.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/v1_routes.py tests/test_background_settings_delete_v1.py` then `git commit -m "feat(background): reset page background settings"`.

### Task 14: Settings deletion fallback integration

**Files:**
- Create: `tests/test_background_settings_regression.py`
- Modify: `tests/test_background_delete_v1.py`
- Test: `tests/test_background_settings_regression.py`

**Interfaces:**
- Consumes: Tasks 8 and 10-13.
- Produces: regression coverage for image reference clearing and global/default inheritance.

- [ ] **Step 1: Write the failing test.** Create global and home settings, delete the selected home image, assert home keeps custom parameters with `background_id:null`, then delete global and assert all effective values use defaults.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_settings_regression -v`; expect fixture or behavior failure.
- [ ] **Step 3: Write the minimal implementation.** Correct route transaction ordering only where needed: update all matching setting references, mark the image deleted, commit, then unlink. Keep Task 10 resolution semantics unchanged.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_settings_regression -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest discover -s tests -v`; expect all tests `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/v1_routes.py tests/test_background_delete_v1.py tests/test_background_settings_regression.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/v1_routes.py tests/test_background_delete_v1.py tests/test_background_settings_regression.py` then `git commit -m "test(background): cover settings inheritance fallback"`.

### Task 15: Controlled legacy custom wallpaper migration

**Files:**
- Create: `backend/background_migration.py`, `tests/test_background_legacy_migration.py`
- Test: `tests/test_background_legacy_migration.py`

**Interfaces:**
- Consumes: a user `custom_wallpaper` value, Task 3 processor, and Task 12 settings SQL.
- Produces: `migrate_legacy_custom_wallpaper(user_id, url, ...) -> bool`, which imports only HTTP/HTTPS URLs.

- [ ] **Step 1: Write the failing test.** Assert non-HTTP values do nothing; success writes one active image plus global setting; request, decode, quota, disk, or database failure leaves `custom_wallpaper` unchanged and no partial DB/file artifact.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_legacy_migration -v`; expect import failure.
- [ ] **Step 3: Write the minimal implementation.** Parse URL with `urlparse`, allow only `http` and `https`, download in the controlled task with `requests.get(..., timeout=(5,20), stream=True)`, pass content through Task 3, then insert image and global setting in one transaction. Do not expose this helper through a user API or modify legacy routes.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_legacy_migration -v`; expect `OK`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest tests.test_auth tests.test_background_settings_regression -v`; expect `OK`.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/background_migration.py tests/test_background_legacy_migration.py`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/background_migration.py tests/test_background_legacy_migration.py` then `git commit -m "feat(background): migrate legacy wallpaper URLs"`.

## Phase 3: Global Frontend Background Rendering

### Task 16: Frontend pure background utilities

**Files:**
- Create: `backend/frontend/src/utils/background.js`, `backend/frontend/scripts/verify-background-utils.mjs`
- Test: `backend/frontend/scripts/verify-background-utils.mjs`

**Interfaces:**
- Consumes: Vue Router route `path` and API persistent settings.
- Produces: `PAGE_TYPES`, `DEFAULT_BACKGROUND_SETTINGS`, `resolvePageType(route)`, and `resolveEffectiveBackground(settingsByPageType,pageType)`.

- [ ] **Step 1: Write the failing test.** Assert `/` maps home, `/categories` and `/category/4` map category, `/favorites` favorites, `/profile` and `/questionnaire` profile, other paths global; assert image and parameter inheritance remain independent.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-background-utils.mjs` from `backend/frontend`; expect module-not-found.
- [ ] **Step 3: Write the minimal implementation.** Export frozen values matching Tasks 10-13. Make `resolveEffectiveBackground` return `{backgroundId,overlayOpacity,blurPx,positionX,positionY,sizeMode}` with page parameter precedence and global image fallback.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-background-utils.mjs`; expect `background utility checks passed`.
- [ ] **Step 5: Run regression checks.** Run `npm run build` and `npm run test:auth-state` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/utils/background.js backend/frontend/scripts/verify-background-utils.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/utils/background.js backend/frontend/scripts/verify-background-utils.mjs` then `git commit -m "feat(background): add frontend background utilities"`.

### Task 17: Pinia background store and Blob lifecycle

**Files:**
- Create: `backend/frontend/src/stores/background.js`, `backend/frontend/scripts/verify-background-store.mjs`
- Modify: `backend/frontend/src/main.js`
- Test: `backend/frontend/scripts/verify-background-store.mjs`

**Interfaces:**
- Consumes: `api`, `unwrapResponse`, `useUserStore`, Task 16 functions, and image endpoint URLs.
- Produces: `initializeForSession`, `loadLibrary`, `loadSettings`, `fetchImageObjectUrl`, `uploadBackground`, `deleteBackground`, `savePageSetting`, `deletePageSetting`, draft methods, modal methods, `revokeObjectUrl`, `revokeAllObjectUrls`, and `reset`.

- [ ] **Step 1: Write the failing test.** Assert the source defines state `library`, `settingsByPageType`, `objectUrlByBackgroundId`, `inflightByBackgroundId`, `draftByPageType`, `isSettingsModalOpen`, `loading`, and `error`; assert image GET uses `responseType:"blob"`, same ID shares a Promise, and reset revokes each URL.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-background-store.mjs` from `backend/frontend`; expect missing store failure.
- [ ] **Step 3: Write the minimal implementation.** Create a setup store. Use `api.get(`/backgrounds/${id}/image`, {responseType:"blob"})`, `URL.createObjectURL(response.data)`, cache only successful URLs, and remove cache plus `URL.revokeObjectURL` on replacement, deletion, and reset. In `main.js`, initialize it after `useUserStore(pinia).initFromStorage()` and before `app.use(router)`.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-background-store.mjs`; expect `background store checks passed`.
- [ ] **Step 5: Run regression checks.** Run `npm run build` and `npm run test:auth-state` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/stores/background.js backend/frontend/src/main.js backend/frontend/scripts/verify-background-store.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/stores/background.js backend/frontend/src/main.js backend/frontend/scripts/verify-background-store.mjs` then `git commit -m "feat(background): add account background store"`.

### Task 18: Session, logout, and route synchronization

**Files:**
- Create: `backend/frontend/scripts/verify-background-session-sync.mjs`
- Modify: `backend/frontend/src/stores/background.js`, `backend/frontend/src/App.vue`
- Test: `backend/frontend/scripts/verify-background-session-sync.mjs`

**Interfaces:**
- Consumes: `userStore.isLoggedIn`, user auth-state listener, and Router current route.
- Produces: background initialization after login/callback/refresh and cleanup on logout or user switch without changing `user.js` authentication behavior.

- [ ] **Step 1: Write the failing test.** Assert a watch on login identity initializes once per session, calls `reset` and `revokeAllObjectUrls` when identity becomes empty or changes, and initialization errors are caught rather than propagated.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-background-session-sync.mjs` from `backend/frontend`; expect assertion failure.
- [ ] **Step 3: Write the minimal implementation.** In the background store watch `() => userStore.isLoggedIn ? userStore.userInfo?.id || userStore.username : null`; call `initializeForSession()` for a new key, and `reset()` before loading a replacement key. In `App.vue` call background-store cleanup in `onBeforeUnmount`; do not edit Authing callbacks or `userStore.logout`.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-background-session-sync.mjs`; expect `background session checks passed`.
- [ ] **Step 5: Run regression checks.** Run `npm run test:auth-state`, `npm run test:ai-unified-entry`, and `npm run build` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/stores/background.js backend/frontend/src/App.vue backend/frontend/scripts/verify-background-session-sync.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/stores/background.js backend/frontend/src/App.vue backend/frontend/scripts/verify-background-session-sync.mjs` then `git commit -m "feat(background): sync backgrounds with account sessions"`.

### Task 19: Fixed three-layer AppBackground renderer

**Files:**
- Create: `backend/frontend/src/components/background/AppBackground.vue`, `backend/frontend/scripts/verify-app-background.mjs`
- Modify: `backend/frontend/src/App.vue`
- Test: `backend/frontend/scripts/verify-app-background.mjs`

**Interfaces:**
- Consumes: Task 16 page type and Task 17 effective setting/Object URL.
- Produces: fixed image, blur, and overlay layers behind `#app-root`.

- [ ] **Step 1: Write the failing test.** Assert three named layers, `position: fixed`, `inset: 0`, `pointer-events: none`, a separate blur element, light/dark overlay colors, and no `filter` on `router-view`.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-app-background.mjs` from `backend/frontend`; expect missing component failure.
- [ ] **Step 3: Write the minimal implementation.** Render image and blur layers from CSS variables for the effective URL, use `background-size` for cover/contain/auto and `background-position: ${x}% ${y}%`, scale blur content slightly to hide edges, and render overlay `rgba(255,255,255,opacity)` or `rgba(15,23,42,opacity)`. Mount `<AppBackground />` before `#app-root`; set `#app-root { position:relative; z-index:1; }`.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-app-background.mjs`; expect `app background checks passed`.
- [ ] **Step 5: Run regression checks.** Run `npm run build`, `npm run test:hero-search-engine-layout`, and `npm run test:category-sites-page` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/components/background/AppBackground.vue backend/frontend/src/App.vue backend/frontend/scripts/verify-app-background.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/components/background/AppBackground.vue backend/frontend/src/App.vue backend/frontend/scripts/verify-app-background.mjs` then `git commit -m "feat(background): render account backgrounds globally"`.

### Task 20: AI assistant panel background reuse

**Files:**
- Create: `backend/frontend/scripts/verify-ai-background.mjs`
- Modify: `backend/frontend/src/components/ai/AiSiteAssistant.vue`
- Test: `backend/frontend/scripts/verify-ai-background.mjs`

**Interfaces:**
- Consumes: Task 17 store effective `ai_assistant` setting and its cached Blob URL.
- Produces: three private visual layers inside `ai-site-assistant__panel`, with existing content above them.

- [ ] **Step 1: Write the failing test.** Assert the AI component imports `useBackgroundStore`, accesses the `ai_assistant` setting, contains no `URL.createObjectURL`, and preserves the existing `aside`/overlay panel.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-ai-background.mjs` from `backend/frontend`; expect missing assertions.
- [ ] **Step 3: Write the minimal implementation.** Add a positioned panel background wrapper with image/blur/overlay siblings, use store-provided Object URL, make the existing panel content `position:relative; z-index:1`, and retain the original solid panel fallback when no URL or Blob request error exists.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-ai-background.mjs`; expect `AI background checks passed`.
- [ ] **Step 5: Run regression checks.** Run `npm run test:ai-site-assistant-panel`, `npm run test:ai-unified-entry`, and `npm run build` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/components/ai/AiSiteAssistant.vue backend/frontend/scripts/verify-ai-background.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/components/ai/AiSiteAssistant.vue backend/frontend/scripts/verify-ai-background.mjs` then `git commit -m "feat(background): render AI panel account background"`.

## Phase 4: Settings UI and Complete Acceptance

### Task 21: Login-only header entry

**Files:**
- Create: `backend/frontend/scripts/verify-background-header-entry.mjs`
- Modify: `backend/frontend/src/components/layout/AppHeader.vue`
- Test: `backend/frontend/scripts/verify-background-header-entry.mjs`

**Interfaces:**
- Consumes: `userStore.isLoggedIn` and Task 17 `openSettingsModal()`.
- Produces: one `button[role="menuitem"]` in the existing avatar dropdown.

- [ ] **Step 1: Write the failing test.** Assert a login-guarded background settings button calls `backgroundStore.openSettingsModal()` then existing `closeMenu()`, creates no new route, and keeps existing `/profile`, `/favorites`, and logout checks.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-background-header-entry.mjs` from `backend/frontend`; expect assertion failure.
- [ ] **Step 3: Write the minimal implementation.** Import the store, add one menu button adjacent to current profile/favorites entries, call `openSettingsModal(); closeMenu();`, and rely on the existing `width:min(320px,calc(100vw - 24px))` dropdown constraints.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-background-header-entry.mjs`; expect `background header entry checks passed`.
- [ ] **Step 5: Run regression checks.** Run `node scripts/verify-user-menu.mjs` and `npm run build` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/components/layout/AppHeader.vue backend/frontend/scripts/verify-background-header-entry.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/components/layout/AppHeader.vue backend/frontend/scripts/verify-background-header-entry.mjs` then `git commit -m "feat(background): add settings menu entry"`.

### Task 22: Accessible singleton settings modal shell

**Files:**
- Create: `backend/frontend/src/components/background/BackgroundSettingsModal.vue`, `backend/frontend/scripts/verify-background-modal.mjs`
- Modify: `backend/frontend/src/App.vue`
- Test: `backend/frontend/scripts/verify-background-modal.mjs`

**Interfaces:**
- Consumes: Task 17 modal/draft methods.
- Produces: one app-root-mounted dialog with `close` behavior and slots for library/preview components.

- [ ] **Step 1: Write the failing test.** Assert `role="dialog"`, `aria-modal="true"`, Escape and backdrop close, initial focus assignment, focus restoration, 375px width constraint, and `discardDraft` on an unsaved close.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-background-modal.mjs` from `backend/frontend`; expect component-not-found.
- [ ] **Step 3: Write the minimal implementation.** Render by `backgroundStore.isSettingsModalOpen`; on open store the trigger element, focus a labelled heading or close button, trap Tab within the dialog, and on close invoke `discardDraft(activePageType)`, `closeSettingsModal()`, then restore focus. Mount exactly one `<BackgroundSettingsModal />` in `App.vue`.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-background-modal.mjs`; expect `background modal checks passed`.
- [ ] **Step 5: Run regression checks.** Run `npm run build` and `node scripts/verify-user-menu.mjs` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/components/background/BackgroundSettingsModal.vue backend/frontend/src/App.vue backend/frontend/scripts/verify-background-modal.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/components/background/BackgroundSettingsModal.vue backend/frontend/src/App.vue backend/frontend/scripts/verify-background-modal.mjs` then `git commit -m "feat(background): add settings modal shell"`.

### Task 23: Background library UI

**Files:**
- Create: `backend/frontend/src/components/background/BackgroundLibrary.vue`, `backend/frontend/scripts/verify-background-library-ui.mjs`
- Modify: `backend/frontend/src/components/background/BackgroundSettingsModal.vue`
- Test: `backend/frontend/scripts/verify-background-library-ui.mjs`

**Interfaces:**
- Consumes: `library`, `uploadBackground(file)`, `deleteBackground(id)`, and cached image URLs.
- Produces: `select`, `upload`, and `delete` events plus visible `n/10` capacity state.

- [ ] **Step 1: Write the failing test.** Assert accept is `image/jpeg,image/png,image/webp`, count is derived from library length, upload disables at ten or pending, same-file reselection clears input value, and delete reports use-state and loading/error states.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-background-library-ui.mjs` from `backend/frontend`; expect missing component failure.
- [ ] **Step 3: Write the minimal implementation.** Use a hidden file input with `@change`, reject files above `10 * 1024 * 1024` before calling the store, emit selected IDs, set `event.target.value=""` in `finally`, disable repeated submissions, and call `fetchImageObjectUrl` for thumbnails. Do not derive server paths in the component.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-background-library-ui.mjs`; expect `background library UI checks passed`.
- [ ] **Step 5: Run regression checks.** Run `npm run build` and `npm run test:favorites-cards-visible` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/components/background/BackgroundLibrary.vue backend/frontend/src/components/background/BackgroundSettingsModal.vue backend/frontend/scripts/verify-background-library-ui.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/components/background/BackgroundLibrary.vue backend/frontend/src/components/background/BackgroundSettingsModal.vue backend/frontend/scripts/verify-background-library-ui.mjs` then `git commit -m "feat(background): add private background library panel"`.

### Task 24: Preview controls and draft persistence boundary

**Files:**
- Create: `backend/frontend/src/components/background/BackgroundPreview.vue`, `backend/frontend/scripts/verify-background-preview.mjs`
- Modify: `backend/frontend/src/components/background/BackgroundSettingsModal.vue`, `backend/frontend/src/stores/background.js`
- Test: `backend/frontend/scripts/verify-background-preview.mjs`

**Interfaces:**
- Consumes: Task 17 drafts and Task 16 effective settings.
- Produces: a local live preview and `savePageSetting(pageType,draft)` only on explicit save.

- [ ] **Step 1: Write the failing test.** Assert controls exist for six page types, image, overlay 0-0.70, blur 0-20, x/y 0-100, and scale modes; assert input handlers call `applyDraft`, save calls `savePageSetting`, reset calls `deletePageSetting`, and cancel calls `discardDraft` without PUT.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-background-preview.mjs` from `backend/frontend`; expect missing component failure.
- [ ] **Step 3: Write the minimal implementation.** Render the same three layers against `draftByPageType[pageType]`, select library images by ID, expose an inherit-image option as `background_id:null`, make `beginDraft(pageType)` copy the persistent record, and update persistent settings only after the save promise resolves.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-background-preview.mjs`; expect `background preview checks passed`.
- [ ] **Step 5: Run regression checks.** Run `node scripts/verify-background-store.mjs` and `npm run build` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/components/background/BackgroundPreview.vue backend/frontend/src/components/background/BackgroundSettingsModal.vue backend/frontend/src/stores/background.js backend/frontend/scripts/verify-background-preview.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/components/background/BackgroundPreview.vue backend/frontend/src/components/background/BackgroundSettingsModal.vue backend/frontend/src/stores/background.js backend/frontend/scripts/verify-background-preview.mjs` then `git commit -m "feat(background): add settings preview drafts"`.

### Task 25: Responsive readability and interaction regression

**Files:**
- Create: `backend/frontend/scripts/verify-background-responsive.mjs`
- Modify: `backend/frontend/src/style.css`, `backend/frontend/src/components/background/AppBackground.vue`, `backend/frontend/src/components/background/BackgroundSettingsModal.vue`
- Test: `backend/frontend/scripts/verify-background-responsive.mjs`

**Interfaces:**
- Consumes: rendered layers and existing page/card CSS selectors.
- Produces: transparent page roots where safe, readable content surfaces, and no horizontal overflow at 375px.

- [ ] **Step 1: Write the failing test.** Assert background surfaces retain `pointer-events:none`; modal uses `max-width:calc(100vw - 24px)`; no rule makes search, cards, header, or profile panel fully transparent; and no `filter` targets RouterView.
- [ ] **Step 2: Run the failing test.** Run `node scripts/verify-background-responsive.mjs` from `backend/frontend`; expect assertion failure.
- [ ] **Step 3: Write the minimal implementation.** Adjust only root page backgrounds to transparent or low-opacity surfaces, retain high-contrast panel/card/header backgrounds, add modal `overflow-x:hidden`, and add 375px grid/sizing rules. Manually inspect 1440, 1024, 768, and 375 widths in light/dark themes with cover, contain, 20px blur, and overlays 0/0.70.
- [ ] **Step 4: Run the focused test.** Run `node scripts/verify-background-responsive.mjs`; expect `background responsive checks passed`.
- [ ] **Step 5: Run regression checks.** Run `npm run build`, `npm run test:hero-search-engine-layout`, `npm run test:category-sites-page`, and `npm run test:favorites-cards-visible` from `backend/frontend`; expect success.
- [ ] **Step 6: Inspect the change.** Run `git diff -- backend/frontend/src/style.css backend/frontend/src/components/background/AppBackground.vue backend/frontend/src/components/background/BackgroundSettingsModal.vue backend/frontend/scripts/verify-background-responsive.mjs`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add backend/frontend/src/style.css backend/frontend/src/components/background/AppBackground.vue backend/frontend/src/components/background/BackgroundSettingsModal.vue backend/frontend/scripts/verify-background-responsive.mjs` then `git commit -m "fix(background): preserve responsive readability"`.

### Task 26: Complete acceptance and deployment documentation

**Files:**
- Create: `tests/test_background_end_to_end.py`, `backend/frontend/scripts/verify-background-integration.mjs`
- Modify: `DEPLOY_VERCEL.md`
- Test: `tests/test_background_end_to_end.py`, `backend/frontend/scripts/verify-background-integration.mjs`

**Interfaces:**
- Consumes: Tasks 1-25.
- Produces: documented deployment preconditions and one full cross-layer acceptance record.

- [ ] **Step 1: Write the failing test.** Backend fixture verifies upload, library, private read, settings, inherit, user isolation, missing disk file, delete, database rollback, and safe logging. Frontend script verifies modal singleton, login recovery, route changes, AI isolation, save/cancel/reset, user switch, logout revoke, and no main-page white screen source pattern.
- [ ] **Step 2: Run the failing test.** Run `python -m unittest tests.test_background_end_to_end -v` and `node scripts/verify-background-integration.mjs` from `backend/frontend`; expect missing acceptance artifacts.
- [ ] **Step 3: Write the minimal implementation.** Add deterministic mocks/fixtures rather than production changes. Document `BACKGROUND_UPLOAD_ROOT`, applying `backend/sql/migrations/20260723_user_backgrounds.up.sql`, Pillow installation, backup and persistent-volume requirements, prohibition on committing private images, Vercel/serverless limitation, and the object-storage migration path.
- [ ] **Step 4: Run the focused test.** Run `python -m unittest tests.test_background_end_to_end -v` and `node scripts/verify-background-integration.mjs` from `backend/frontend`; expect `OK` and `background integration checks passed`.
- [ ] **Step 5: Run regression checks.** Run `python -m unittest discover -s tests -v`; then from `backend/frontend` run `npm run build`, `npm run test:auth-state`, `npm run test:ai-unified-entry`, `npm run test:category-sites-page`, and `npm run test:favorites-cards-visible`; expect every command to succeed.
- [ ] **Step 6: Inspect the change.** Run `git diff -- tests/test_background_end_to_end.py backend/frontend/scripts/verify-background-integration.mjs DEPLOY_VERCEL.md`; allow only those files.
- [ ] **Step 7: Commit.** Run `git add tests/test_background_end_to_end.py backend/frontend/scripts/verify-background-integration.mjs DEPLOY_VERCEL.md` then `git commit -m "docs(background): document local storage deployment"`.

## Planned Commit Boundaries

1. `feat(background): add background schema`
2. `feat(background): configure private upload storage`
3. `feat(background): process private background images`
4. `feat(background): secure private file cleanup`
5. `feat(background): add private background library read API`
6. `feat(background): add private background upload API`
7. `feat(background): add private background image API`
8. `feat(background): add private background deletion`
9. `test(background): cover private library acceptance`
10. `feat(background): validate page settings`
11. `feat(background): read page background settings`
12. `feat(background): save per-page background settings`
13. `feat(background): reset page background settings`
14. `test(background): cover settings inheritance fallback`
15. `feat(background): migrate legacy wallpaper URLs`
16. `feat(background): add frontend background utilities`
17. `feat(background): add account background store`
18. `feat(background): sync backgrounds with account sessions`
19. `feat(background): render account backgrounds globally`
20. `feat(background): render AI panel account background`
21. `feat(background): add settings menu entry`
22. `feat(background): add settings modal shell`
23. `feat(background): add private background library panel`
24. `feat(background): add settings preview drafts`
25. `fix(background): preserve responsive readability`
26. `docs(background): document local storage deployment`

## Plan Self-Review

- Spec coverage: all four phases cover DDL, Pillow, private storage/API, settings/inheritance, legacy `custom_wallpaper`, Store/Blob lifecycle, AppBackground, AI panel, header/menu, modal, responsive checks, and persistent-volume deployment limits.
- Placeholder scan: no unfinished markers, generic error-handling directions, or cross-task references are used as implementation instructions.
- Consistency: API paths, six page types, defaults, size constraints, ownership checks, error codes, and store method names match the approved design throughout.
- Safety: every private route derives server paths from owned database rows; upload/database failures clean files; deletion never restores references after an unlink error; browser URLs are revoked; Authing and recommendation systems remain untouched.

Plan complete and saved to `docs/superpowers/plans/2026-07-23-user-background-customization-implementation-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, with review between tasks.
2. Inline Execution - execute the tasks in this session using execution checkpoints.

Which approach?
