# V1.0 Authentication Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:verification-before-completion while implementing this plan. Execute each task in order and keep unrelated working-tree changes intact.

**Goal:** Unify local/Authing authentication state, secure Authing exchange, refresh JWTs safely, and verify the complete V1.0 auth loop without changing existing UI or non-auth business logic.

**Architecture:** A dependency-free frontend `auth.js` owns browser authentication persistence and legacy-token migration. Pinia mirrors that state, while Axios uses one shared refresh promise and excludes authentication endpoints from refresh handling. The backend keeps the existing authorization-code flow, stores a 60-second opaque exchange code in Redis with atomic GETDEL semantics, and returns the same AuthSession shape from local login and Authing exchange.

**Tech Stack:** Flask, Flask-JWT-Extended, Redis, MySQL/PyMySQL, Vue 3, Pinia, Axios, Node built-in `assert`, Python `unittest`.

## Global Constraints

- Do not change existing login, registration, or homepage visual layout.
- Do not modify search, search-engine selection, categories, career recommendations, hot websites, or AI assistant behavior.
- Do not change Authing, SMTP, database, JWT, or other real credential values.
- Keep `access_token` as the primary access token and retain `token` only as a compatibility alias.
- Never put project JWT, user information, password, or secrets in the Authing callback URL.
- Exchange code must use `secrets.token_urlsafe(32)`, TTL 60 seconds, and atomic single-use retrieval.
- Do not introduce a large frontend or backend test framework.
- Do not push GitHub.

## File Map

- Create: `backend/frontend/src/utils/auth.js` — browser auth keys, session normalization, save/clear, token migration.
- Create: `backend/frontend/scripts/verify-auth-state.mjs` — dependency-free auth storage smoke test.
- Modify: `backend/frontend/src/utils/api.js` — shared session parsing, auth endpoint helpers, single-flight refresh interceptor.
- Modify: `backend/frontend/src/stores/user.js` — Pinia mirror of the shared auth session.
- Modify: `backend/frontend/src/main.js` — initialize the user store once.
- Modify: `backend/frontend/src/router/index.js` — route guards based on `getAccessToken()`.
- Modify: `backend/frontend/src/views/Login.vue` — shared session save and safe redirect/error handling.
- Modify: `backend/frontend/src/views/AuthingCallback.vue` — exchange-code flow and shared session save.
- Modify: `backend/frontend/src/views/Questionnaire.vue` — shared auth reads, session update, and logout.
- Modify: `backend/frontend/src/components/layout/AppHeader.vue` — Pinia-backed display and unified logout.
- Modify: `backend/frontend/src/views/Home.vue`, `CategoryDetail.vue`, `SearchResults.vue`, `SiteDetail.vue` — replace direct auth-token checks only where currently used for auth UI/actions.
- Modify: `backend/frontend/package.json` — add the auth smoke-test command.
- Modify: `backend/app.py` — auth payload helpers, secure redirect handling, Authing exchange-code issuance, local login/register validation, and `/api/auth/me`.
- Modify: `backend/app_extensions.py` — keep the standard refresh endpoint as the sole implementation for `/api/auth/refresh`.
- Modify: `backend/v1_routes.py` — add the JWT-protected current-user endpoint if it is not placed in `app.py`; preserve database-backed admin checks.
- Create: `tests/test_auth.py` — backend auth behavior tests using fake Redis/database boundaries.

## Task 1: Frontend auth utility and RED tests

**Files:** Create `backend/frontend/src/utils/auth.js` and `backend/frontend/scripts/verify-auth-state.mjs`; modify `backend/frontend/package.json`.

- [ ] Write the smoke test first. Use a fake `localStorage`, import the utility, save a complete session, assert all eight keys plus the legacy alias, clear it, assert every key is absent, set only a valid legacy token, call `getAccessToken()`, and assert migration to `access_token`.
- [ ] Run `npm run test:auth-state`; it must fail because the utility/script command is not implemented.
- [ ] Implement `AUTH_STORAGE_KEYS`, `normalizeAuthSession`, `saveAuthSession`, `clearAuthSession`, `getAccessToken`, `getRefreshToken`, and `isValidAuthToken`. Use `access_token` first, copy a valid legacy `token` to `access_token` once, and make `clearAuthSession()` remove `token`, `access_token`, `refresh_token`, `user`, `user_info`, `user_role`, `questionnaire_completed`, and `is_logged_in`.
- [ ] Add `"test:auth-state": "node scripts/verify-auth-state.mjs"` to the frontend scripts.
- [ ] Run the smoke test again and confirm it passes before moving on.

## Task 2: Backend exchange-code primitives and RED tests

**Files:** Modify `backend/app.py`; create `tests/test_auth.py`.

- [ ] Add failing tests for a secure exchange code: patch the random generator and Redis boundary, assert a 60-second `setex`, assert stored data contains only user id and safe redirect, assert the second exchange is rejected, assert expired/unknown code returns 400/401, assert Redis errors return 503, and assert external redirects are rejected before storage.
- [ ] Run the focused backend test with UTF-8 output: `$env:PYTHONIOENCODING='utf-8'; & '.venv\\Scripts\\python.exe' -m unittest tests.test_auth.AuthExchangeTests -v`. Confirm the new assertions fail for missing behavior.
- [ ] Implement a strict `normalize_frontend_redirect()` that accepts only a single-slash relative path and rejects schemes, hosts, double slash, backslash, and control characters.
- [ ] Implement `issue_authing_exchange_code(user_id, redirect)` using `secrets.token_urlsafe(32)` and Redis `setex(..., 60, minimal_json)`. Do not store Authing access tokens or secrets.
- [ ] Implement atomic retrieval with Redis `getdel` when available and a Lua `GET`/`DEL` script fallback otherwise. Never use a plain GET followed by a separate DELETE for exchange redemption.
- [ ] Add `POST /api/authing/exchange`; it must validate the opaque code, atomically consume it, load the user by id, create project access/refresh tokens, and return the common AuthSession data structure. Return 503 for Redis failures and 400/401 for invalid or already-used codes.
- [ ] Update Authing callback to issue the code and redirect only with the opaque code plus validated redirect. If Redis is unavailable, return the explicit Authing service error and never fall back to a JWT URL.
- [ ] Run the focused exchange tests and confirm they pass.

## Task 3: Backend local auth, current-user, and refresh tests

**Files:** Modify `backend/app.py`, `backend/app_extensions.py`, `backend/v1_routes.py`; extend `tests/test_auth.py`.

- [ ] Add failing tests for missing registration username/email/password/code, invalid email, short password, missing login account/password, wrong password 401, successful local login common `data` fields, `/api/auth/me` JWT protection, refresh-token-only behavior, and database-backed admin rejection for a normal user.
- [ ] Run the focused tests and confirm expected failures.
- [ ] Normalize registration input with `request.get_json(silent=True) or {}`, trim username/email, lowercase email, validate email and password length, and return explicit duplicate username versus duplicate email errors. Read Redis safely, return 503 on Redis failure, write the code only after mail succeeds, and delete it only after a successful database commit.
- [ ] Normalize local login account whitespace, preserve password characters, keep username/email lookup, return the common AuthSession under `data` plus old top-level compatibility fields, and retain 400/401/429 statuses.
- [ ] Add JWT-protected `/api/auth/me` returning `user_info`, `user_role`, and `questionnaire_completed` from the database. Do not use local storage values for authorization.
- [ ] Keep `/api/auth/refresh` implemented with `verify_jwt_in_request(refresh=True)` and return only a newly signed access token; retain `/api/refresh` as a compatibility alias without weakening refresh-token validation.
- [ ] Run the focused tests and confirm they pass.

## Task 4: Pinia and Axios session integration

**Files:** Modify `backend/frontend/src/utils/api.js`, `backend/frontend/src/stores/user.js`, `backend/frontend/src/main.js`.

- [ ] Add frontend test coverage for normalized local/Authing session payloads and ensure refresh endpoint errors are not routed back into refresh logic.
- [ ] Run the relevant smoke tests and confirm the new assertions fail before implementation.
- [ ] Replace duplicated session parsing and deletion in `api.js` with imports from `auth.js`. Keep `storeUserSessionFromPayload` as a compatibility wrapper that calls `saveAuthSession` and prefers `payload.data`.
- [ ] Implement a module-level `refreshPromise`. On a business 401 with no `_retry` and a refresh token, request `/auth/refresh` once with `skipAuth` metadata, save the returned access token, mark `_retry`, and replay the original request. Exclude login, register, send-code, reset-code, Authing exchange, refresh, logout, and callback errors. On failure, clear once and redirect to `/login` with a safe internal redirect.
- [ ] Ensure the request interceptor attaches only `getAccessToken()` and never treats `is_logged_in` or `user_role` as proof of authentication.
- [ ] Update Pinia to mirror access token, refresh token, user info, role, and questionnaire state from `auth.js`; make `logout()` call `clearAuthSession()` then reset defaults. Initialize the store from `main.js` after Pinia installation.
- [ ] Run frontend auth smoke tests and the existing build to verify the integration.

## Task 5: Login, Authing callback, route guards, and logout consumers

**Files:** Modify `Login.vue`, `AuthingCallback.vue`, `router/index.js`, `AppHeader.vue`, `Questionnaire.vue`, `Home.vue`, `CategoryDetail.vue`, `SearchResults.vue`, and `SiteDetail.vue`.

- [ ] Add/extend smoke assertions for login and Authing both calling the shared session-saving path and for all logout consumers calling the same clear path.
- [ ] Run the smoke test and confirm the new assertions fail before implementation.
- [ ] In `Login.vue`, parse the common `data` payload first, call `saveAuthSession` or the store method, preserve existing UI, keep explicit 401 account/password messaging, and normalize `redirect` before `router.replace`.
- [ ] In `AuthingCallback.vue`, accept only the opaque `code`, call `POST /authing/exchange`, save the returned common session, optionally call `/auth/me` only if exchange does not contain complete user data, and clear all state on any failure. Never read or write user info from URL parameters.
- [ ] In the router, use `getAccessToken()` and `isValidAuthToken()` for `requiresAuth`; keep `user_role` only as a client-side admin navigation hint while server endpoints remain authoritative. Preserve safe internal redirects.
- [ ] Change `AppHeader` and questionnaire re-login to use Pinia `logout()` and `router.replace`, not localStorage deletion lists. Use the store/shared token utility for the remaining auth UI checks without changing rendered layout.
- [ ] Run frontend auth smoke tests and build.

## Task 6: Full verification and handoff

**Files:** No new implementation files; inspect all diffs and tests.

- [ ] Run `& '.venv\\Scripts\\python.exe' -m py_compile backend/app.py backend/authing_service.py backend/v1_routes.py` from the repository root.
- [ ] Run existing Python tests with UTF-8 output: `$env:PYTHONIOENCODING='utf-8'; & '.venv\\Scripts\\python.exe' -m unittest tests.test_vercel_deploy`.
- [ ] Run the new auth tests with UTF-8 output: `$env:PYTHONIOENCODING='utf-8'; & '.venv\\Scripts\\python.exe' -m unittest tests.test_auth -v`.
- [ ] Run `npm run test:auth-state` and `npm run build` from `backend/frontend`.
- [ ] Inspect `git diff --check`, `git status --short`, and the complete diff to confirm no UI/non-auth business files changed and no credentials were modified.
- [ ] Report only commands actually run, passed checks, external-service limitations, manual acceptance steps, and a suggested commit message. Do not claim Redis/MySQL/SMTP/Authing live success without live evidence.
