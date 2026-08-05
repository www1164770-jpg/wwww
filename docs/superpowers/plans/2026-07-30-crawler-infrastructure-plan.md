# Crawler Infrastructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立与现有 Flask/正式数据库隔离、可通过 SQLite 测试并具备 MySQL 生产租赁语义的 Phase 1 爬虫基础设施。

**Architecture:** `backend/crawler/` 使用独立 SQLAlchemy Declarative Base、engine/session、向前迁移和模块 CLI；普通应用不导入或连接它。任务、run、worker 和 outbox 通过同一 crawler session 在事务中变更，MySQL 租赁使用 `FOR UPDATE SKIP LOCKED`，SQLite 提供语义一致的顺序测试。

**Tech Stack:** Python 3.13、SQLAlchemy 2.0、PyMySQL、MySQL 8、SQLite、标准库 unittest/argparse/logging。

## Global Constraints

- `CRAWLER_DATABASE_URL` 无默认值，只在运行爬虫 CLI 时必需，不读取现有 `MYSQL_*` 或 `DB_*`。
- 正式迁移目标数据库名只能是 `zhihui_crawler`；测试目标名必须包含 `test`；不提供危险覆盖开关。
- 默认值精确为：icons `backend/data/crawler/icons`、logs `backend/data/crawler/logs`、lease `300`、attempts `3`、nightly target `3000`、start `01:00`、stop `05:00`。
- 运行时不得自动迁移、seed、创建 worker、创建管理员或启动夜间抓取。
- 不修改现有前端、职业推荐、SiteCard、收藏、API、正式数据库模型和业务迁移。
- 不添加 Scrapy、Playwright、Ollama 或 Phase 2–5 依赖。
- 所有步骤保持当前 Git 暂存边界，不执行任何 Git 状态变更操作。
- 新测试先处于预期失败，再进行最小实现并运行相关回归。

## File Map

| 文件 | 单一职责 |
| --- | --- |
| `backend/crawler/config/settings.py` | 解析、验证 crawler 环境变量和仓库相对路径 |
| `backend/crawler/db/base.py` | 独立 Declarative Base、UTC 和可移植主键类型 |
| `backend/crawler/db/models.py` | 五张 Phase 1 ORM 表和索引 |
| `backend/crawler/db/session.py` | 仅从 CrawlerSettings 创建 engine/session |
| `backend/crawler/db/migration.py` | 迁移目标安全校验和向前迁移 runner |
| `backend/crawler/db/migrations/0001_initial.sql` | MySQL 8 初始表和索引 |
| `backend/crawler/queue/states.py` | 任务状态常量、合法转换和错误 |
| `backend/crawler/queue/tasks.py` | URL 基础规范化、入队、租赁、完成、失败、取消、重试和恢复 |
| `backend/crawler/workers/heartbeats.py` | worker 注册、心跳、停止和 stale 派生 |
| `backend/crawler/scheduler/runs.py` | run 创建、停止请求、完成和活跃查询 |
| `backend/crawler/outbox/service.py` | outbox 幂等入队、租赁、完成和失败 |
| `backend/crawler/observability/json_logging.py` | JSON formatter、错误截断和递归脱敏 |
| `backend/crawler/cli/__init__.py` | argparse 命令实现与依赖边界 |
| `backend/crawler/cli/__main__.py` | `python -m backend.crawler.cli` 入口 |
| `tests/crawler/support.py` | SQLite engine/session 和固定时钟辅助 |
| `tests/crawler/test_*.py` | 各责任模块的 RED/GREEN 行为测试 |
| `backend/data/crawler/README.md` | 运行目录用途和不得提交的数据说明 |
| `backend/crawler/.env.example` | 无秘密 crawler 配置样例 |
| `.gitignore` | icons/logs/tmp/pids 运行数据忽略与 README/.gitkeep 例外 |

---

### Task 1: 独立配置与应用隔离

**Files:**

- Create: `backend/crawler/__init__.py`
- Create: `backend/crawler/config/__init__.py`
- Create: `backend/crawler/config/settings.py`
- Create: `backend/crawler/.env.example`
- Create: `tests/crawler/__init__.py`
- Create: `tests/crawler/test_config.py`

**Interfaces:**

- Produces: `CrawlerConfigError(ValueError)`
- Produces: `CrawlerSettings.from_env(environ: Mapping[str, str] | None = None, *, require_database: bool = False) -> CrawlerSettings`
- Produces fields: `database_url: str | None`, `icon_root: Path`, `log_root: Path`, `worker_id: str`, `lease_seconds: int`, `max_attempts: int`, `nightly_target: int`, `start_time: time`, `stop_time: time`

- [ ] **Step 1: Write failing configuration and application-isolation tests**

```python
class CrawlerSettingsTests(unittest.TestCase):
    def test_defaults_do_not_require_database_url(self):
        settings = CrawlerSettings.from_env({})
        self.assertIsNone(settings.database_url)
        self.assertTrue(settings.icon_root.is_absolute())
        self.assertTrue(str(settings.icon_root).endswith("backend\\data\\crawler\\icons"))
        self.assertEqual(settings.lease_seconds, 300)
        self.assertEqual(settings.start_time, time(1, 0))

    def test_cli_mode_requires_database_url(self):
        with self.assertRaisesRegex(CrawlerConfigError, "CRAWLER_DATABASE_URL"):
            CrawlerSettings.from_env({}, require_database=True)

    def test_invalid_positive_integer_and_window_are_rejected(self):
        with self.assertRaises(CrawlerConfigError):
            CrawlerSettings.from_env({"CRAWLER_LEASE_SECONDS": "-1"})
        with self.assertRaises(CrawlerConfigError):
            CrawlerSettings.from_env({
                "CRAWLER_START_TIME": "05:00",
                "CRAWLER_STOP_TIME": "01:00",
            })

    def test_importing_existing_app_does_not_require_crawler_database_url(self):
        # subprocess removes CRAWLER_DATABASE_URL and imports backend/app.py
        self.assertEqual(result.returncode, 0)
```

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tests.crawler.test_config -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.crawler'`.

- [ ] **Step 3: Implement immutable settings parsing**

Implement a frozen dataclass. Resolve relative icon/log paths from `Path(__file__).resolve().parents[3]`, create no directories during parsing, derive default worker ID as `<hostname>-<pid>`, parse positive integers strictly, parse `HH:MM`, and require `start_time < stop_time`.

- [ ] **Step 4: Document configuration without secrets**

Write the nine crawler variables to `backend/crawler/.env.example`. Leave `CRAWLER_DATABASE_URL=` empty and explain that it must target the independent `zhihui_crawler` database. Keeping the crawler example separate also preserves the repository's existing staged `backend/.env.example` boundary.

- [ ] **Step 5: Run and verify GREEN**

Run: `python -m unittest tests.crawler.test_config -v`

Expected: all configuration tests PASS; application import subprocess exits 0.

- [ ] **Step 6: Run related regression**

Run: `python -m unittest tests.test_backend_runtime_config -v`

Expected: existing runtime configuration tests PASS and crawler config is never imported by `backend/app.py`.

---

### Task 2: Independent ORM schema and safe migration

**Files:**

- Create: `backend/crawler/db/__init__.py`
- Create: `backend/crawler/db/base.py`
- Create: `backend/crawler/db/models.py`
- Create: `backend/crawler/db/session.py`
- Create: `backend/crawler/db/migration.py`
- Create: `backend/crawler/db/migrations/0001_initial.sql`
- Create: `tests/crawler/support.py`
- Create: `tests/crawler/test_models_migration.py`
- Create: `tests/crawler/test_mysql_contract.py`
- Create: `tests/crawler/test_mysql_integration.py`

**Interfaces:**

- Produces: `CrawlerBase(DeclarativeBase)`
- Produces models: `CrawlRun`, `CrawlTask`, `WorkerHeartbeat`, `CrawlerSetting`, `OutboxEvent`
- Produces: `create_crawler_engine(settings: CrawlerSettings) -> Engine`
- Produces: `create_session_factory(engine: Engine) -> sessionmaker[Session]`
- Produces: `session_scope(factory: sessionmaker[Session]) -> ContextManager[Session]`
- Produces: `validate_migration_target(database_url: str) -> str`
- Produces: `run_migrations(engine: Engine, database_url: str) -> MigrationResult`

- [ ] **Step 1: Write failing schema and safety tests**

```python
class CrawlerSchemaTests(unittest.TestCase):
    def test_schema_contains_only_phase_one_tables(self):
        self.assertEqual(
            set(CrawlerBase.metadata.tables),
            {"crawl_runs", "crawl_tasks", "worker_heartbeats",
             "crawler_settings", "outbox_events"},
        )

    def test_active_task_dedupe_is_database_enforced(self):
        # Insert two pending rows with the same task_type/active_dedupe_key.
        with self.assertRaises(IntegrityError):
            session.flush()

    def test_terminal_rows_release_active_dedupe_slot(self):
        # Multiple rows with active_dedupe_key=None are accepted.
        session.flush()

    def test_migration_refuses_formal_project_database(self):
        with self.assertRaisesRegex(MigrationSafetyError, "refused"):
            validate_migration_target("mysql+pymysql://u:p@h/nav_site")

    def test_migration_allows_only_crawler_or_explicit_test_name(self):
        self.assertEqual(
            validate_migration_target("mysql+pymysql://u:p@h/zhihui_crawler"),
            "zhihui_crawler",
        )
        self.assertEqual(
            validate_migration_target("mysql+pymysql://u:p@h/zhihui_crawler_test"),
            "zhihui_crawler_test",
        )
```

Also compile the lease select with MySQL dialect and assert uppercase SQL contains `FOR UPDATE SKIP LOCKED`.

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tests.crawler.test_models_migration tests.crawler.test_mysql_contract -v`

Expected: FAIL because crawler DB modules and models do not exist.

- [ ] **Step 3: Implement portable ORM models**

Use `BigInteger().with_variant(Integer, "sqlite")` for autoincrement IDs, SQLAlchemy `JSON`, UTC-naive `DateTime`, string statuses, explicit unique constraints and indexes. Add nullable `active_dedupe_key` with unique `(task_type, active_dedupe_key)` while retaining stable `dedupe_key`.

- [ ] **Step 4: Implement isolated engine/session**

`create_crawler_engine()` must raise `CrawlerConfigError` when no crawler URL is present, use `pool_pre_ping=True`, and never import `backend.models`, `backend.db_pool` or Flask. `session_scope()` commits on success, rolls back on any exception and always closes.

- [ ] **Step 5: Implement MySQL-only forward migration**

`validate_migration_target()` accepts MySQL URLs whose database is exactly `zhihui_crawler` or contains the case-insensitive token `test`; it rejects missing database, SQLite and every other name. `run_migrations()` records version `0001_initial` in `crawler_schema_migrations`, executes only unapplied statements, and performs no down/drop/seed action.

- [ ] **Step 6: Add optional MySQL integration guard**

`tests/crawler/test_mysql_integration.py` reads only `CRAWLER_TEST_DATABASE_URL`. If absent it raises `unittest.SkipTest`; if the database name lacks `test`, it fails before connecting. Tests use transactions and delete only rows they created by unique test UID, never truncate or drop the database.

- [ ] **Step 7: Run and verify GREEN**

Run: `python -m unittest tests.crawler.test_models_migration tests.crawler.test_mysql_contract tests.crawler.test_mysql_integration -v`

Expected: SQLite and SQL compilation tests PASS; MySQL integration is SKIPPED when no explicit test URL exists.

---

### Task 3: Central state machine and task enqueue

**Files:**

- Create: `backend/crawler/queue/__init__.py`
- Create: `backend/crawler/queue/states.py`
- Create: `backend/crawler/queue/tasks.py`
- Create: `tests/crawler/test_task_states.py`
- Create: `tests/crawler/test_task_enqueue.py`

**Interfaces:**

- Produces constants: `PENDING`, `LEASED`, `COMPLETED`, `FAILED`, `DEAD`, `CANCELLED`
- Produces: `assert_task_transition(current: str, target: str) -> None`
- Produces: `normalize_task_target(target: str) -> str`
- Produces: `task_target_hash(normalized_target: str) -> str`
- Produces dataclass: `EnqueueResult(task: CrawlTask, created: bool)`
- Produces:

```python
def enqueue_task(
    session: Session,
    *,
    task_type: str,
    target: str,
    payload: dict[str, Any] | None = None,
    priority: int = 100,
    run_id: int | None = None,
    available_at: datetime | None = None,
    dedupe_key: str | None = None,
) -> EnqueueResult: ...
```

- [ ] **Step 1: Write failing state and enqueue tests**

Cover all documented legal transitions; assert `completed -> leased` and `dead -> leased` raise `InvalidTaskTransition`. Test URL normalization, stable hash, active duplicate returns the same task with `created=False`, different task types accept the same target, completed task releases the active slot, and unexpected integrity errors propagate.

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tests.crawler.test_task_states tests.crawler.test_task_enqueue -v`

Expected: FAIL because state and enqueue APIs are absent.

- [ ] **Step 3: Implement centralized state map and basic target normalization**

Normalize HTTP(S) scheme/host, remove fragment and default port, and set empty path to `/`; reject blank task type/target. For non-URL targets trim outer whitespace without interpreting local paths.

- [ ] **Step 4: Implement concurrency-safe enqueue**

Compute `target_hash = sha256(normalized_target)`. Compute `dedupe_key` from the explicit generation key or normalized target, set the same value in `active_dedupe_key`, and insert inside `session.begin_nested()`. On `IntegrityError`, query the active row with the same `(task_type, active_dedupe_key)` and return it; re-raise if no such row exists.

- [ ] **Step 5: Run and verify GREEN**

Run: `python -m unittest tests.crawler.test_task_states tests.crawler.test_task_enqueue -v`

Expected: all state and enqueue tests PASS.

---

### Task 4: MySQL-safe leasing and run stop boundary

**Files:**

- Modify: `backend/crawler/queue/tasks.py`
- Create: `backend/crawler/scheduler/__init__.py`
- Create: `backend/crawler/scheduler/runs.py`
- Create: `tests/crawler/test_task_leasing.py`
- Create: `tests/crawler/test_crawl_runs.py`

**Interfaces:**

- Produces: `build_lease_query(*, task_types: Sequence[str], now: datetime, limit: int) -> Select`
- Produces:

```python
def lease_tasks(
    session: Session,
    *,
    worker_id: str,
    task_types: list[str],
    limit: int,
    lease_seconds: int,
    now: datetime,
) -> list[CrawlTask]: ...
```

- Produces: `create_run(session: Session, *, run_uid: str, scheduled_for: datetime, target_count: int, now: datetime) -> RunCreationResult`
- Produces: `request_run_stop(session: Session, *, run_uid: str, now: datetime) -> CrawlRun`
- Produces: `finish_run(session: Session, *, run_uid: str, status: str, now: datetime) -> CrawlRun`
- Produces: `get_active_run(session: Session) -> CrawlRun | None`

- [ ] **Step 1: Write failing run and lease tests**

Tests assert:

- only due pending tasks are leased;
- lower priority number wins, then available/created/id order;
- fields `worker_id`, `leased_at`, `leased_until`, status are set;
- second worker gets no already leased task;
- limit 0 and 101 raise `ValueError`;
- empty task types raise;
- create run UID is idempotent;
- stop_requested prevents new leasing for that run;
- a task leased before stop can still complete;
- active run lookup returns running or stop_requested only.

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tests.crawler.test_task_leasing tests.crawler.test_crawl_runs -v`

Expected: FAIL because run and lease functions are absent.

- [ ] **Step 3: Implement crawl run state transitions**

Use centralized run constants `running`, `stop_requested`, `completed`, `failed`, `cancelled`. `request_run_stop()` only changes running rows. `finish_run()` accepts completed/failed/cancelled and stamps `finished_at`.

- [ ] **Step 4: Implement leasing transaction**

Build a single SQLAlchemy select that outer joins `CrawlRun`, permits tasks without run or with `run.status == running`, orders deterministically, applies `.limit(limit).with_for_update(skip_locked=True)`, then updates selected ORM rows before the surrounding transaction commits. Increment `run.leased_count` in the same session.

- [ ] **Step 5: Run and verify GREEN**

Run: `python -m unittest tests.crawler.test_task_leasing tests.crawler.test_crawl_runs tests.crawler.test_mysql_contract -v`

Expected: SQLite semantics PASS and MySQL compiled SQL contains `FOR UPDATE SKIP LOCKED`.

---

### Task 5: Completion, retry, failure and lease recovery

**Files:**

- Modify: `backend/crawler/queue/tasks.py`
- Create: `tests/crawler/test_task_failure.py`
- Create: `tests/crawler/test_lease_recovery.py`

**Interfaces:**

- Produces: `retry_delay_seconds(attempt_count: int, *, random_value: float | None = None) -> float`
- Produces: `complete_task(session: Session, *, task_uid: str, worker_id: str, now: datetime) -> CrawlTask`
- Produces: `fail_task(session: Session, *, task_uid: str, worker_id: str, error_code: str, error_message: str, now: datetime, random_value: float | None = None) -> CrawlTask`
- Produces: `retry_due_failed_tasks(session: Session, *, now: datetime, limit: int = 100) -> int`
- Produces: `cancel_task(session: Session, *, task_uid: str, now: datetime) -> CrawlTask`
- Produces dataclass: `RecoveryResult(recovered_count: int, dead_count: int)`
- Produces: `recover_expired_leases(session: Session, *, now: datetime, random_value: float | None = None) -> RecoveryResult`

- [ ] **Step 1: Write failing completion/failure/recovery tests**

Cover:

- only owning worker completes/fails a lease;
- completion clears active dedupe and cannot be leased again;
- failure increments attempts, truncates/sanitizes error and schedules exponential backoff;
- due failed rows become pending;
- max attempts becomes dead and clears active dedupe;
- pending/failed cancellation works; terminal cancellation is rejected;
- expired lease returns pending or dead, clears all lease fields;
- repeated recovery is idempotent;
- run completed/failed cached counts update in the same transaction.

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tests.crawler.test_task_failure tests.crawler.test_lease_recovery -v`

Expected: FAIL because lifecycle functions are absent.

- [ ] **Step 3: Implement bounded error handling and backoff**

Use base delay 30 seconds, exponent `2 ** (attempt_count - 1)`, cap 3,600 seconds, and ±10% jitter derived from injectable `random_value`. Restrict error code to 64 chars and error message to 1,000 sanitized chars.

- [ ] **Step 4: Implement lifecycle mutations**

Every API fetches with row lock where supported, validates state/worker ownership, clears lease fields, updates `updated_at`, and updates run cached counters. On terminal states set `active_dedupe_key=None`.

- [ ] **Step 5: Implement idempotent expired lease recovery**

Select only `leased` rows with non-null `leased_until < now`, use bounded batch and `FOR UPDATE SKIP LOCKED`, increment once, and return separate recovered/dead counts.

- [ ] **Step 6: Run and verify GREEN**

Run: `python -m unittest tests.crawler.test_task_failure tests.crawler.test_lease_recovery -v`

Expected: all lifecycle tests PASS.

---

### Task 6: Worker heartbeat

**Files:**

- Create: `backend/crawler/workers/__init__.py`
- Create: `backend/crawler/workers/heartbeats.py`
- Create: `tests/crawler/test_worker_heartbeat.py`

**Interfaces:**

- Produces: `register_worker(session: Session, *, worker_id: str, worker_type: str, process_id: int, hostname: str, now: datetime, metadata: dict[str, Any] | None = None) -> WorkerHeartbeat`
- Produces: `heartbeat_worker(session: Session, *, worker_id: str, now: datetime, current_task_uid: str | None = None, metadata: dict[str, Any] | None = None) -> WorkerHeartbeat`
- Produces: `mark_worker_stopped(session: Session, *, worker_id: str, now: datetime) -> WorkerHeartbeat`
- Produces: `worker_effective_status(worker: WorkerHeartbeat, *, now: datetime, stale_after_seconds: int) -> str`

- [ ] **Step 1: Write failing heartbeat tests**

Test unique registration updates the existing row, heartbeat updates last seen/current task, explicit stopped remains stopped, online becomes stale after threshold, and metadata recursively redacts password/token/Cookie/Authorization keys before persistence.

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tests.crawler.test_worker_heartbeat -v`

Expected: FAIL because heartbeat APIs are absent.

- [ ] **Step 3: Implement worker lifecycle**

Persist only `online` and `stopped`; derive `stale` from `last_seen_at`. Re-registration resets status online and start time. Heartbeat for an unknown worker raises `WorkerNotFound`.

- [ ] **Step 4: Run and verify GREEN**

Run: `python -m unittest tests.crawler.test_worker_heartbeat -v`

Expected: all worker tests PASS and stored metadata contains `[REDACTED]` instead of secret values.

---

### Task 7: Outbox primitives

**Files:**

- Create: `backend/crawler/outbox/__init__.py`
- Create: `backend/crawler/outbox/service.py`
- Create: `tests/crawler/test_outbox.py`

**Interfaces:**

- Produces dataclass: `OutboxEnqueueResult(event: OutboxEvent, created: bool)`
- Produces: `enqueue_outbox_event(session: Session, *, event_uid: str, aggregate_type: str, aggregate_uid: str, event_type: str, payload: dict[str, Any], available_at: datetime | None = None) -> OutboxEnqueueResult`
- Produces: `lease_outbox_events(session: Session, *, worker_id: str, limit: int, lease_seconds: int, now: datetime) -> list[OutboxEvent]`
- Produces: `mark_outbox_processed(session: Session, *, event_uid: str, worker_id: str, now: datetime) -> OutboxEvent`
- Produces: `fail_outbox_event(session: Session, *, event_uid: str, worker_id: str, error_message: str, now: datetime, random_value: float | None = None) -> OutboxEvent`

- [ ] **Step 1: Write failing outbox tests**

Test duplicate `event_uid` returns existing row with `created=False`, leasing is ordered and bounded, processed event never leases again, wrong worker cannot finish/fail, retry schedules availability, max attempts becomes dead, and log records never include full payload.

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tests.crawler.test_outbox -v`

Expected: FAIL because outbox service does not exist.

- [ ] **Step 3: Implement outbox queue**

Use statuses `pending`, `leased`, `processed`, `dead`. Enqueue catches only the event UID uniqueness collision. Lease uses the same bounded MySQL row-lock pattern. Failure returns to pending with backoff until its model `max_attempts`, then dead.

- [ ] **Step 4: Run and verify GREEN**

Run: `python -m unittest tests.crawler.test_outbox tests.crawler.test_mysql_contract -v`

Expected: outbox semantics PASS and MySQL outbox lease SQL has `FOR UPDATE SKIP LOCKED`.

---

### Task 8: Structured JSON logging and runtime directories

**Files:**

- Create: `backend/crawler/observability/__init__.py`
- Create: `backend/crawler/observability/json_logging.py`
- Create: `backend/data/crawler/README.md`
- Create: `backend/data/crawler/icons/.gitkeep`
- Create: `backend/data/crawler/logs/.gitkeep`
- Create: `backend/data/crawler/tmp/.gitkeep`
- Create: `backend/data/crawler/pids/.gitkeep`
- Create: `tests/crawler/test_logging_redaction.py`
- Modify: `.gitignore`

**Interfaces:**

- Produces: `redact_sensitive(value: Any, *, key: str | None = None) -> Any`
- Produces: `sanitize_error_message(message: str, *, max_length: int = 1000) -> str`
- Produces: `CrawlerJsonFormatter(logging.Formatter)`
- Produces: `configure_crawler_logging(settings: CrawlerSettings, *, component: str, stream: TextIO | None = None) -> logging.Logger`
- Produces: `log_event(logger: logging.Logger, event: str, **fields: Any) -> None`

- [ ] **Step 1: Write failing redaction and JSON schema tests**

Test nested dict/list redaction, case-insensitive Authorization/Cookie/password/token keys, database URL password removal, error truncation, valid single-line JSON and presence of all nine required fields. Test file-handler failure falls back to stderr without exposing the path or exception detail.

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tests.crawler.test_logging_redaction -v`

Expected: FAIL because observability module is absent.

- [ ] **Step 3: Implement recursive redaction and formatter**

The formatter always emits `timestamp`, `level`, `component`, `event`, `worker_id`, `run_uid`, `task_uid`, `duration_ms`, `error_code`; absent values are JSON null. Extra structured fields are sanitized under `details`. Exception text is represented by a bounded error class/code, not traceback body in normal logs.

- [ ] **Step 4: Add runtime ignore rules**

Add:

```gitignore
backend/data/crawler/icons/*
backend/data/crawler/logs/*
backend/data/crawler/tmp/*
backend/data/crawler/pids/*
!backend/data/crawler/icons/.gitkeep
!backend/data/crawler/logs/.gitkeep
!backend/data/crawler/tmp/.gitkeep
!backend/data/crawler/pids/.gitkeep
!backend/data/crawler/**/README.md
```

- [ ] **Step 5: Run and verify GREEN**

Run: `python -m unittest tests.crawler.test_logging_redaction -v`

Expected: JSON schema and all sensitive-data tests PASS.

---

### Task 9: Safe module CLI

**Files:**

- Create: `backend/crawler/cli/__init__.py`
- Create: `backend/crawler/cli/__main__.py`
- Create: `tests/crawler/test_cli.py`

**Interfaces:**

- Produces: `build_parser() -> argparse.ArgumentParser`
- Produces: `main(argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int`
- Commands: `db-check`, `migrate`, `enqueue-smoke-task`, `lease-smoke-task`, `recover-expired`, `worker-status`, `run-create`, `run-stop`, `status`
- Each subcommand accepts `--json` after the command.

- [ ] **Step 1: Write failing CLI tests**

Test all command names appear in help; missing URL returns nonzero and names only `CRAWLER_DATABASE_URL`; `status --json` emits one valid JSON object; a mocked database exception returns nonzero with `database_unavailable`, never the empty-task success shape; URL password never appears; commands do not start a worker.

- [ ] **Step 2: Run and verify RED**

Run: `python -m unittest tests.crawler.test_cli -v`

Expected: FAIL because CLI module is absent.

- [ ] **Step 3: Implement parser, output envelope and dependency boundary**

Each invocation calls `CrawlerSettings.from_env(..., require_database=True)` before creating its isolated engine. JSON success envelope is `{"ok": true, "command": "...", "data": {...}}`; errors are `{"ok": false, "command": "...", "error": {"code": "...", "message": "..."}}`. Human output remains concise. Catch configuration and SQLAlchemy database errors separately and return nonzero.

- [ ] **Step 4: Implement commands**

- `db-check`: execute `SELECT 1`.
- `migrate`: run only safe crawler migrations.
- `enqueue-smoke-task`: enqueue one `smoke` task for `https://example.com/`, optionally attached to active run.
- `lease-smoke-task`: register configured worker, lease at most one `smoke` task.
- `recover-expired`: recover expired leases.
- `worker-status`: list stored worker identity and derived status without metadata secrets.
- `run-create`: create a run UID from UTC timestamp plus random suffix.
- `run-stop`: request stop on the active running run.
- `status`: return run/task/outbox counts and worker status summary.

- [ ] **Step 5: Run and verify GREEN**

Run: `python -m unittest tests.crawler.test_cli -v`

Expected: all CLI tests PASS.

- [ ] **Step 6: Verify real missing-config behavior**

Run with `CRAWLER_DATABASE_URL` absent:

`python -m backend.crawler.cli status --json`

Expected: nonzero exit; stdout/stderr contains valid safe error JSON naming `CRAWLER_DATABASE_URL`, with no connection URL.

---

### Task 10: Phase 1 integrated verification

**Files:**

- Modify only Phase 1 files if a failing verification identifies a defect within the approved boundary.

**Interfaces:**

- Consumes all Phase 1 APIs and preserves existing application behavior.

- [ ] **Step 1: Run all crawler tests**

Run: `python -m unittest discover -s tests/crawler -p "test_*.py" -v`

Expected: all SQLite/unit/CLI/SQL compilation tests PASS; MySQL integration reports SKIPPED when `CRAWLER_TEST_DATABASE_URL` is absent.

- [ ] **Step 2: Run syntax validation**

Run: `python -m compileall -q backend tests`

Expected: exit 0 with no syntax errors.

- [ ] **Step 3: Run existing Python career/recommendation regressions**

Run:

```text
python -m unittest tests.test_occupation_utils tests.test_recommend_sort_v1 -v
```

Expected: tests PASS; if a test requires pytest-only fixtures, report the precise runner limitation and run each unittest-compatible module separately.

- [ ] **Step 4: Run frontend build and directed checks**

Run:

```text
npm.cmd run build --prefix backend/frontend
npm.cmd run test:auth-state --prefix backend/frontend
npm.cmd run test:api-base-url --prefix backend/frontend
npm.cmd run test:home-ai-recommend --prefix backend/frontend
npm.cmd run test:career-recommendation --prefix backend/frontend
npm.cmd run test:site-favorites --prefix backend/frontend
```

Expected: every command exits 0; no frontend files are changed by Phase 1.

- [ ] **Step 5: Run diff hygiene**

Run: `git diff --check`

Expected: exit 0 with no whitespace errors.

- [ ] **Step 6: Validate repository boundary**

Record:

```text
git status --short
git diff --stat
git diff --cached --name-only
git ls-files --others --exclude-standard
```

Expected: the original staged file count remains 31; crawler source, tests, documents and approved config/runtime-ignore changes are unstaged or untracked; no cache, database, log, PID, icon binary, secret or virtual environment appears.

- [ ] **Step 7: Run safe MySQL smoke only when explicitly configured**

First check whether `CRAWLER_TEST_DATABASE_URL` exists without printing its value. If absent, mark the MySQL smoke as not executed. If present, validate the database name contains `test` before connecting, then run migration, db-check, run/task/two-worker/recovery/heartbeat/stop/outbox/status checks using unique smoke UIDs and delete only those test rows after completion.

Expected: no connection to the formal database under any circumstance; absence of a test database is reported as a verification limitation, not success.
