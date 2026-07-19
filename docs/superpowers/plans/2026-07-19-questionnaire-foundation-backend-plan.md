# Questionnaire Foundation Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立新版问卷后台基础数据模型、迁移和管理员只读查询接口，同时保持现有问卷、认证和推荐功能不变。

**Architecture:** 在现有 Flask 单体中新增独立的问卷基础领域模块，模型继续使用现有全局 `models.db`，避免改变应用工厂或拆分 `app.py`。原生 MySQL SQL 迁移采用受版本控制的升级/回退文件和最小迁移运行器；管理员只读路由在独立模块中复用 JWT 后查 `users.role` 的现有安全模式，读取服务使用 SQLAlchemy 的显式预加载组装版本快照。

**Tech Stack:** Python 3.14（当前 `backend/venv` 运行时）；Flask 3.1.3；Flask-SQLAlchemy 3.1.1；SQLAlchemy 2.0.50；PyMySQL 1.2.0；Flask-JWT-Extended 4.7.4；MySQL（当前配置使用 `mysql+pymysql`、`utf8mb4`，仓库未声明服务端最低版本）；`unittest` 与 `unittest.mock`。

## Global Constraints

1. 保持 `/api/questionnaire`、`/api/questionnaire/submit`、`/api/questionnaire/my` 的旧问卷功能可用。
2. 不修改 Authing 配置、认证流程、推荐算法或 `/questionnaire` 前台入口。
3. 本阶段新增 API 只允许 `GET`，不得实现发布、停用、回滚、草稿、答卷、匿名化或任何问卷写接口。
4. 已发布版本和后续历史答卷必须可使用自身快照；本阶段只建立快照定义结构，不写入答卷。
5. 稳定题目编码固定为 `question_code`，稳定选项值固定为 `option_value`。
6. `admin` 与 `super_admin` 可读取，`user` 与匿名请求不可读取；鉴权必须以后端重新查询的 `users.role` 为准。
7. 任何响应、日志和错误不得暴露密码、Token、Secret、连接串或数据库堆栈。
8. 当前数据库方言是 MySQL，不能使用 PostgreSQL 部分唯一索引；字符集继续使用 `utf8mb4`。
9. 生产表结构仅通过版本化 SQL 迁移改变；不得依赖 `db.create_all()` 修改已有生产表。
10. 所有任务遵循先失败测试、最小实现、目标测试、回归测试、独立提交的顺序。
11. 不改变已确认的业务规则：旧问卷并行、停止操作 1 秒保存、草稿 30 天过期且再保留 90 天、匿名化而非账号注销、回滚复制新草稿。

---

## Investigation Record

- `backend/app.py` 在模块级创建 `app = Flask(__name__)`，配置 `mysql+pymysql`，调用 `db.init_app(app)`，并在运行入口的 `initialize_database()` 内调用一次 `db.create_all()`。
- `backend/models.py` 是当前 Flask-SQLAlchemy 模型集中位置，并导出唯一的 `db = SQLAlchemy()`。
- `backend/v1_routes.py` 通过 `register_v1_routes(app, get_db_connection)` 注册路由；其响应格式为 `{"code", "legacy_code", "message", "msg", "data"}`，管理员装饰器在 JWT 身份确定后查询 `users.role`，只允许 `admin` 和 `super_admin`。
- `backend/sql/migrations/` 当前包含两个幂等 MySQL SQL 文件；不存在 Flask-Migrate、Alembic 目录、`Migrate(...)` 调用或受控迁移运行器。
- `tests/` 使用 `unittest`、`unittest.mock` 和源码/假连接断言；当前没有创建或清理真实 MySQL 测试库的夹具。
- 旧问卷由 `backend/v1_routes.py` 中的 `/api/questionnaire*` 路由和 `user_profiles`、`users.questionnaire_completed`、`users.has_survey`、`users.user_tags`、`users.interests` 驱动，第一阶段不得触碰这些路径或字段。

## File Structure

| 文件 | 动作 | 单一职责 |
| --- | --- | --- |
| `backend/questionnaire_constants.py` | Create | 集中保存字符串枚举集合、字段长度和只读筛选白名单。 |
| `backend/questionnaire_models.py` | Create | 定义六个问卷基础表及关系、唯一约束和数据库级外键。 |
| `backend/questionnaire_validation.py` | Create | 校验题目、选项和条件的跨行规则；不处理 HTTP。 |
| `backend/questionnaire_read_service.py` | Create | 分页、筛选、预加载和只读快照序列化。 |
| `backend/questionnaire_admin_read_routes.py` | Create | 管理员 JWT/角色检查、查询参数解析和 GET 响应。 |
| `backend/scripts/run_sql_migration.py` | Create | 按名称执行受控的 `.up.sql` 或 `.down.sql`，并记录 `schema_migrations`。 |
| `backend/sql/migrations/20260719_questionnaire_foundation.up.sql` | Create | 按外键依赖顺序建立六张新表、索引和约束。 |
| `backend/sql/migrations/20260719_questionnaire_foundation.down.sql` | Create | 仅在六张新表均未被后续表引用时按反向顺序删除它们。 |
| `backend/app.py` | Modify | 导入模型模块以供 SQLAlchemy 发现，并注册只读管理员路由；不调整既有路由。 |
| `tests/questionnaire_foundation_test_support.py` | Create | 提供隔离的 SQLAlchemy SQLite 内存会话、假 MySQL 游标和 JWT 请求辅助工具。 |
| `tests/test_questionnaire_foundation_models.py` | Create | 覆盖六类实体的结构、唯一性和规则校验。 |
| `tests/test_questionnaire_foundation_migration.py` | Create | 覆盖迁移文件、运行器、升级/回退顺序及旧表保护。 |
| `tests/test_questionnaire_foundation_read_api.py` | Create | 覆盖管理员只读端点、分页、筛选、响应结构和预加载查询。 |
| `tests/test_questionnaire_foundation_regression.py` | Create | 覆盖旧问卷、认证、推荐和既有管理员接口未被改变。 |

不把新代码继续堆入 `backend/app.py` 或 `backend/models.py`：前者已同时承担应用配置和大量路由，后者应继续只暴露既有模型及 `db`。`questionnaire_models.py` 只导入 `models.db`，不导入 `app`；`questionnaire_read_service.py` 只导入问卷模型和常量；路由模块只导入服务和 JWT 工具，因此不存在从模型回导入应用的循环。`app.py` 只在 `db.init_app(app)` 后注册路由，并在模型模块导入后让 SQLAlchemy 元数据可见。测试夹具集中在一个支持文件中，避免每个测试重复构造数据库和假连接。

## Migration Strategy

当前仓库没有正式迁移框架，因此第一项实现引入最小、受版本控制的 SQL 迁移运行器，不引入 Alembic 或 Flask-Migrate。运行器维护 `schema_migrations(name VARCHAR(128) PRIMARY KEY, applied_at DATETIME NOT NULL)`，仅接受 `20260719_questionnaire_foundation`，并从同目录读取固定命名的升级和回退文件；它不会读取任意文件路径。

升级命令为 `python backend/scripts/run_sql_migration.py upgrade 20260719_questionnaire_foundation`；回退命令为 `python backend/scripts/run_sql_migration.py downgrade 20260719_questionnaire_foundation`。测试库使用显式环境变量 `QUESTIONNAIRE_TEST_DB_NAME=nav_site_questionnaire_test`；运行器拒绝空名称和 `nav_site`，防止测试命令触及默认库。持续集成在隔离 MySQL 实例中设置该变量后执行升级、模型/读取测试和回退；本地未设置变量时，MySQL 集成类明确跳过，SQLite 内存测试仍覆盖 Python 和 ORM 规则。

升级顺序为 `occupations`、`questionnaire_definitions`、`questionnaire_versions`、`questionnaire_questions`、`questionnaire_options`、`questionnaire_conditions`；回退反向执行。所有外键使用 `ON DELETE RESTRICT`，已发布版本和未来历史快照无法通过级联删除丢失。新表创建使用 `CREATE TABLE IF NOT EXISTS`、`ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`；旧 `users`、`user_profiles` 和旧问卷字段不执行任何 DDL。新职业不在此阶段插入初始化数据，避免把固定字典和写入业务混入基础层。

对于 MySQL 不支持部分唯一索引的事实，`questionnaire_versions.current_effective_scope_key` 使用可空唯一键：草稿、停用和归档版本保存 `NULL`，未来发布事务把适用范围键写入此列并把被替代版本改回 `NULL`。MySQL 唯一索引允许多个 `NULL`，因此可在不依赖部分唯一索引的情况下限制每个范围最多一个当前生效版本；本计划不实现发布写入逻辑。

## Read API Contract

所有端点位于 `/api/admin/questionnaire-foundation`，仅接受 `GET`，使用当前 V1 成功结构：

```json
{"code": 200, "legacy_code": 0, "message": "success", "msg": "success", "data": {}}
```

分页列表的 `data` 固定为：

```json
{
  "items": [],
  "pagination": {"page": 1, "per_page": 20, "total": 0, "pages": 0}
}
```

400、401、403、404 分别返回 `{"code": 400|401|403|404, "message": "...", "msg": "...", "data": {}}`，不含数据库异常。端点如下：

| GET 路径 | 查询参数 | `data` |
| --- | --- | --- |
| `/occupations` | `page`, `per_page`, `q`, `enabled` | 分页职业：`id`、`occupation_code`、`name`、`category`、`sort_order`、`enabled`、`new_occupation_policy`。 |
| `/definitions` | `page`, `per_page`, `q`, `enabled`, `scope_type`, `occupation_code`, `user_type` | 分页定义：稳定 `definition_code`、范围字段、当前版本摘要。 |
| `/definitions/<definition_id>` | 无 | 单一完整定义及其版本摘要；不存在为 404。 |
| `/definitions/<definition_id>/versions` | `page`, `per_page`, `status` | 版本分页：`id`、`version_number`、`status`、`source_version_id`、`is_current_effective`、时间戳。 |
| `/versions/<version_id>` | 无 | 版本元数据及按排序的题目、选项和条件快照。 |
| `/versions/<version_id>/preview` | 无 | 与版本详情相同的不可变快照结构，另含 `preview: true`。 |

题目对象固定为 `{"id", "question_code", "title", "description", "question_type", "required", "sort_order", "enabled", "is_general", "min_selections", "max_selections", "max_length", "options", "condition"}`；选项对象固定为 `{"id", "option_value", "label", "sort_order", "enabled"}`；条件对象固定为 `{"id", "source_question_code", "operator", "expected_option_value", "target_question_code"}`。服务用 `selectinload` 预加载 `questions.options`、`questions.target_condition` 和条件来源，禁止在循环中再次查询。

### Task 1: Add the controlled SQL migration runner and test scaffold

**Files:**
- Create: `backend/scripts/run_sql_migration.py`
- Create: `tests/questionnaire_foundation_test_support.py`
- Create: `tests/test_questionnaire_foundation_migration.py`

**Interfaces:**
- Consumes: `backend/db_pool.py:get_connection`, `backend/sql/migrations/`.
- Produces: `run_migration(direction: str, name: str, connection_factory) -> None`; `QUESTIONNAIRE_TEST_DB_NAME` test gate; `MigrationRunnerTests`.

- [ ] **Step 1: Write the failing migration-runner tests**

```python
class MigrationRunnerTests(unittest.TestCase):
    def test_rejects_unknown_migration_name(self):
        with self.assertRaisesRegex(ValueError, "unsupported migration"):
            run_migration("upgrade", "arbitrary.sql", lambda: FakeConnection())

    def test_refuses_default_database_name(self):
        with patch.dict(os.environ, {"QUESTIONNAIRE_TEST_DB_NAME": "nav_site"}):
            with self.assertRaisesRegex(RuntimeError, "refusing default database"):
                require_test_database_name()
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_questionnaire_foundation_migration.MigrationRunnerTests -v`

Expected: `ImportError` because `run_sql_migration` and its exported functions do not exist.

- [ ] **Step 3: Implement the minimal runner and support helpers**

```python
ALLOWED_MIGRATIONS = frozenset({"20260719_questionnaire_foundation"})

def run_migration(direction, name, connection_factory):
    if direction not in {"upgrade", "downgrade"}:
        raise ValueError("direction must be upgrade or downgrade")
    if name not in ALLOWED_MIGRATIONS:
        raise ValueError("unsupported migration")
    sql_path = MIGRATIONS_DIR / f"{name}.{ 'up' if direction == 'upgrade' else 'down' }.sql"
    with connection_factory() as connection:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_MIGRATIONS_SQL)
            for statement in split_sql(sql_path.read_text(encoding="utf-8")):
                cursor.execute(statement)
        connection.commit()
```

`tests/questionnaire_foundation_test_support.py` defines `FakeCursor.executed: list[tuple[str, tuple]]`, `FakeConnection.commit()`, `FakeConnection.rollback()` and `require_test_database_name()`; it rejects `""` and `"nav_site"` before connecting.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `python -m unittest tests.test_questionnaire_foundation_migration.MigrationRunnerTests -v`

Expected: both tests report `ok`.

- [ ] **Step 5: Run migration-runner regression tests**

Run: `python -m unittest tests.test_db_startup tests.test_questionnaire_v1_regression -v`

Expected: all existing tests report `OK`; no application import runs a migration.

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/run_sql_migration.py tests/questionnaire_foundation_test_support.py tests/test_questionnaire_foundation_migration.py
git commit -m "feat(questionnaire): add controlled SQL migration runner"
```

### Task 2: Add the occupation foundation model and migration

**Files:**
- Create: `backend/questionnaire_constants.py`
- Create: `backend/questionnaire_models.py`
- Create: `backend/sql/migrations/20260719_questionnaire_foundation.up.sql`
- Create: `backend/sql/migrations/20260719_questionnaire_foundation.down.sql`
- Create: `tests/test_questionnaire_foundation_models.py`

**Interfaces:**
- Consumes: `backend/models.py:db`, Task 1 migration runner.
- Produces: `Occupation`, `NEW_OCCUPATION_POLICIES`, `validate_occupation()`; `occupations` table.

- [ ] **Step 1: Write failing occupation tests**

```python
def test_occupation_code_and_name_are_unique(self):
    session.add_all([Occupation("software_engineer", "Software Engineer"),
                     Occupation("software_engineer", "Designer")])
    with self.assertRaises(IntegrityError):
        session.commit()

def test_occupation_policy_is_limited_to_documented_values(self):
    with self.assertRaisesRegex(ValueError, "new_occupation_policy"):
        validate_occupation({"occupation_code": "analyst", "new_occupation_policy": "open"})
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_questionnaire_foundation_models.OccupationModelTests -v`

Expected: `ModuleNotFoundError` for `questionnaire_models`.

- [ ] **Step 3: Implement occupation constants, model and DDL**

```python
NEW_OCCUPATION_POLICIES = frozenset({"use_general", "closed"})

class Occupation(db.Model):
    __tablename__ = "occupations"
    id = db.Column(db.Integer, primary_key=True)
    occupation_code = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    category = db.Column(db.String(120), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    new_occupation_policy = db.Column(db.String(32), nullable=False, default="use_general")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
```

The upgrade SQL creates `occupations` with `uq_occupations_code` and `uq_occupations_name`; the down SQL drops it only after future tables are absent. `validate_occupation` checks the constant set before persistence. No seed row is inserted.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `python -m unittest tests.test_questionnaire_foundation_models.OccupationModelTests -v`

Expected: uniqueness and policy tests report `ok`.

- [ ] **Step 5: Run migration structure tests**

Run: `python -m unittest tests.test_questionnaire_foundation_migration tests.test_questionnaire_foundation_models.OccupationModelTests -v`

Expected: `occupations` is first in upgrade order and last in down order; all tests report `OK`.

- [ ] **Step 6: Commit**

```bash
git add backend/questionnaire_constants.py backend/questionnaire_models.py backend/sql/migrations/20260719_questionnaire_foundation.up.sql backend/sql/migrations/20260719_questionnaire_foundation.down.sql tests/test_questionnaire_foundation_models.py tests/test_questionnaire_foundation_migration.py
git commit -m "feat(questionnaire): add occupation foundation model"
```

### Task 3: Add questionnaire definitions and versions

**Files:**
- Modify: `backend/questionnaire_constants.py: scope, user-type and version-status sets`
- Modify: `backend/questionnaire_models.py: QuestionnaireDefinition and QuestionnaireVersion`
- Modify: `backend/sql/migrations/20260719_questionnaire_foundation.up.sql: definitions and versions DDL`
- Modify: `backend/sql/migrations/20260719_questionnaire_foundation.down.sql: reverse DDL`
- Modify: `tests/test_questionnaire_foundation_models.py: DefinitionVersionModelTests`

**Interfaces:**
- Consumes: `Occupation`, `users.id`, constants from Task 2.
- Produces: `QuestionnaireDefinition`, `QuestionnaireVersion`, `build_scope_key(scope_type, occupation_code, user_type)` and `validate_definition_scope()`.

- [ ] **Step 1: Write failing definition/version tests**

```python
def test_scope_key_is_unique_and_encodes_the_scope(self):
    self.assertEqual(build_scope_key("occupation", "designer", None), "occupation:designer")
    with self.assertRaisesRegex(ValueError, "occupation_id"):
        validate_definition_scope("occupation", None, None)

def test_version_number_is_unique_per_definition(self):
    session.add_all([QuestionnaireVersion(definition_id=1, version_number=1),
                     QuestionnaireVersion(definition_id=1, version_number=1)])
    with self.assertRaises(IntegrityError):
        session.commit()
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_questionnaire_foundation_models.DefinitionVersionModelTests -v`

Expected: `ImportError` for `QuestionnaireDefinition` or `QuestionnaireVersion`.

- [ ] **Step 3: Implement models and scope constraints**

```python
QUESTIONNAIRE_SCOPE_TYPES = frozenset({"general", "occupation", "user_type", "occupation_user_type"})
USER_TYPES = frozenset({"student", "employed", "organization"})
QUESTIONNAIRE_VERSION_STATUSES = frozenset({"draft", "published", "disabled", "archived"})

class QuestionnaireDefinition(db.Model):
    __tablename__ = "questionnaire_definitions"
    __table_args__ = (db.UniqueConstraint("scope_key", name="uq_questionnaire_definitions_scope_key"),)
    id = db.Column(db.Integer, primary_key=True)
    definition_code = db.Column(db.String(96), nullable=False, unique=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    scope_type = db.Column(db.String(32), nullable=False)
    scope_key = db.Column(db.String(192), nullable=False)
    occupation_id = db.Column(db.Integer, db.ForeignKey("occupations.id", ondelete="RESTRICT"))
    user_type = db.Column(db.String(32), nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)

class QuestionnaireVersion(db.Model):
    __tablename__ = "questionnaire_versions"
    __table_args__ = (db.UniqueConstraint("definition_id", "version_number", name="uq_questionnaire_versions_number"),
                      db.UniqueConstraint("current_effective_scope_key", name="uq_questionnaire_versions_effective_scope"))
    id = db.Column(db.Integer, primary_key=True)
    definition_id = db.Column(db.Integer, db.ForeignKey("questionnaire_definitions.id", ondelete="RESTRICT"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="draft")
    source_version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_versions.id", ondelete="RESTRICT"))
    current_effective_scope_key = db.Column(db.String(192), nullable=True)
```

The migration adds creator/publisher foreign keys to `users.id`, `created_at`, `published_at`, `is_current_effective`, description, and supporting indexes. Validation enforces the four allowed scope shapes and all documented string values before future writes.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `python -m unittest tests.test_questionnaire_foundation_models.DefinitionVersionModelTests -v`

Expected: scope and per-definition version uniqueness tests report `ok`.

- [ ] **Step 5: Run related model regression tests**

Run: `python -m unittest tests.test_questionnaire_foundation_models.OccupationModelTests tests.test_questionnaire_foundation_models.DefinitionVersionModelTests -v`

Expected: all tests report `OK`; no test imports `app.py` to alter tables.

- [ ] **Step 6: Commit**

```bash
git add backend/questionnaire_constants.py backend/questionnaire_models.py backend/sql/migrations/20260719_questionnaire_foundation.up.sql backend/sql/migrations/20260719_questionnaire_foundation.down.sql tests/test_questionnaire_foundation_models.py
git commit -m "feat(questionnaire): add definitions and versions"
```

### Task 4: Add questions and options with stable codes

**Files:**
- Modify: `backend/questionnaire_constants.py: QUESTION_TYPES`
- Modify: `backend/questionnaire_models.py: QuestionnaireQuestion and QuestionnaireOption`
- Modify: `backend/questionnaire_validation.py: validate_question_shape and validate_option_shape`
- Modify: `backend/sql/migrations/20260719_questionnaire_foundation.up.sql: questions/options DDL`
- Modify: `backend/sql/migrations/20260719_questionnaire_foundation.down.sql: reverse DDL`
- Modify: `tests/test_questionnaire_foundation_models.py: QuestionOptionModelTests`

**Interfaces:**
- Consumes: `QuestionnaireVersion`, constants.
- Produces: `QuestionnaireQuestion`, `QuestionnaireOption`, `validate_question_shape(question) -> None`, `validate_option_shape(option) -> None`.

- [ ] **Step 1: Write failing question/option tests**

```python
def test_question_code_is_unique_only_within_a_version(self):
    add_question(version_id=1, question_code="skill_level")
    add_question(version_id=2, question_code="skill_level")
    with self.assertRaises(IntegrityError):
        add_question(version_id=1, question_code="skill_level")

def test_question_type_specific_constraints_are_rejected(self):
    with self.assertRaisesRegex(ValueError, "multiple_choice"):
        validate_question_shape(question_type="single_choice", min_selections=1, max_selections=2, max_length=None)
    with self.assertRaisesRegex(ValueError, "max_length"):
        validate_question_shape(question_type="short_text", min_selections=None, max_selections=None, max_length=0)
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_questionnaire_foundation_models.QuestionOptionModelTests -v`

Expected: missing model classes or validation functions cause failure.

- [ ] **Step 3: Implement model fields, unique keys and validation**

```python
QUESTION_TYPES = frozenset({"single_choice", "multiple_choice", "short_text"})

class QuestionnaireQuestion(db.Model):
    __tablename__ = "questionnaire_questions"
    __table_args__ = (db.UniqueConstraint("version_id", "question_code", name="uq_questionnaire_questions_code"),)
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_versions.id", ondelete="RESTRICT"), nullable=False)
    question_code = db.Column(db.String(96), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    question_type = db.Column(db.String(32), nullable=False)
    required = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    is_general = db.Column(db.Boolean, nullable=False, default=False)
    min_selections = db.Column(db.Integer)
    max_selections = db.Column(db.Integer)
    max_length = db.Column(db.Integer)

class QuestionnaireOption(db.Model):
    __tablename__ = "questionnaire_options"
    __table_args__ = (db.UniqueConstraint("question_id", "option_value", name="uq_questionnaire_options_value"),)
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questionnaire_questions.id", ondelete="RESTRICT"), nullable=False)
    option_value = db.Column(db.String(120), nullable=False)
    label = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
```

Validation accepts only the three question types; `multiple_choice` requires positive minimum/maximum values with minimum not greater than maximum; `short_text` requires positive `max_length` and no selection bounds; `single_choice` has neither selection bounds nor text length. Option validation rejects options for `short_text`.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `python -m unittest tests.test_questionnaire_foundation_models.QuestionOptionModelTests -v`

Expected: uniqueness, cross-version reuse and invalid shape cases report `ok`.

- [ ] **Step 5: Run related regression tests**

Run: `python -m unittest tests.test_questionnaire_foundation_models tests.test_questionnaire_v1_regression -v`

Expected: all tests report `OK`; the old V1 migration still references only its four user fields.

- [ ] **Step 6: Commit**

```bash
git add backend/questionnaire_constants.py backend/questionnaire_models.py backend/questionnaire_validation.py backend/sql/migrations/20260719_questionnaire_foundation.up.sql backend/sql/migrations/20260719_questionnaire_foundation.down.sql tests/test_questionnaire_foundation_models.py
git commit -m "feat(questionnaire): add question and option models"
```

### Task 5: Add simple condition persistence and graph validation

**Files:**
- Modify: `backend/questionnaire_constants.py: CONDITION_OPERATORS`
- Modify: `backend/questionnaire_models.py: QuestionnaireCondition`
- Modify: `backend/questionnaire_validation.py: validate_condition`
- Modify: `backend/sql/migrations/20260719_questionnaire_foundation.up.sql: conditions DDL`
- Modify: `backend/sql/migrations/20260719_questionnaire_foundation.down.sql: reverse DDL`
- Modify: `tests/test_questionnaire_foundation_models.py: ConditionModelTests`

**Interfaces:**
- Consumes: `QuestionnaireQuestion`, `QuestionnaireOption`, `QuestionnaireVersion`.
- Produces: `QuestionnaireCondition`; `validate_condition(source, target, expected_option, operator) -> None`.

- [ ] **Step 1: Write failing condition tests**

```python
def test_condition_requires_source_before_target_and_one_target_rule(self):
    with self.assertRaisesRegex(ValueError, "source question must precede target"):
        validate_condition(source=question(sort_order=20), target=question(sort_order=10), expected_option=option(), operator="equals")
    add_condition(target_question_id=9)
    with self.assertRaises(IntegrityError):
        add_condition(target_question_id=9)

def test_condition_operator_and_option_membership_are_checked(self):
    with self.assertRaisesRegex(ValueError, "equals requires single_choice"):
        validate_condition(source=question(question_type="multiple_choice"), target=question(), expected_option=option(), operator="equals")
    with self.assertRaisesRegex(ValueError, "source option"):
        validate_condition(source=question(), target=question(), expected_option=option(question_id=99), operator="equals")
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_questionnaire_foundation_models.ConditionModelTests -v`

Expected: `QuestionnaireCondition` and `validate_condition` are not defined.

- [ ] **Step 3: Implement condition model and validator**

```python
CONDITION_OPERATORS = frozenset({"equals", "contains"})

class QuestionnaireCondition(db.Model):
    __tablename__ = "questionnaire_conditions"
    __table_args__ = (db.UniqueConstraint("target_question_id", name="uq_questionnaire_conditions_target"),)
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_versions.id", ondelete="RESTRICT"), nullable=False)
    source_question_id = db.Column(db.Integer, db.ForeignKey("questionnaire_questions.id", ondelete="RESTRICT"), nullable=False)
    target_question_id = db.Column(db.Integer, db.ForeignKey("questionnaire_questions.id", ondelete="RESTRICT"), nullable=False)
    source_question_code = db.Column(db.String(96), nullable=False)
    target_question_code = db.Column(db.String(96), nullable=False)
    operator = db.Column(db.String(16), nullable=False)
    expected_option_value = db.Column(db.String(120), nullable=False)
```

`validate_condition` requires all three records to share `version_id`, source and target IDs to differ, source sort order to be lower, `equals` to use `single_choice`, `contains` to use `multiple_choice`, and expected option ownership by the source. The future write service will call this validator before persistence; the unique target key enforces the one-condition rule now.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `python -m unittest tests.test_questionnaire_foundation_models.ConditionModelTests -v`

Expected: all source/target/operator/option tests report `ok`.

- [ ] **Step 5: Run complete model tests**

Run: `python -m unittest tests.test_questionnaire_foundation_models -v`

Expected: all six-entity model cases report `OK`.

- [ ] **Step 6: Commit**

```bash
git add backend/questionnaire_constants.py backend/questionnaire_models.py backend/questionnaire_validation.py backend/sql/migrations/20260719_questionnaire_foundation.up.sql backend/sql/migrations/20260719_questionnaire_foundation.down.sql tests/test_questionnaire_foundation_models.py
git commit -m "feat(questionnaire): add simple condition foundation"
```

### Task 6: Implement the read service and snapshot serializers

**Files:**
- Create: `backend/questionnaire_read_service.py`
- Create: `tests/test_questionnaire_foundation_read_api.py`
- Modify: `backend/questionnaire_models.py: relationship declarations only`

**Interfaces:**
- Consumes: all Task 2–5 models and `sqlalchemy.orm.selectinload`.
- Produces: `list_occupations(filters) -> dict`, `list_definitions(filters) -> dict`, `get_definition(definition_id) -> dict | None`, `list_versions(definition_id, filters) -> dict`, `get_version_snapshot(version_id) -> dict | None`.

- [ ] **Step 1: Write failing service tests**

```python
def test_version_snapshot_orders_nested_records_without_n_plus_one(self):
    snapshot = get_version_snapshot(version_id=7)
    self.assertEqual([q["question_code"] for q in snapshot["questions"]], ["occupation", "interests"])
    self.assertEqual(snapshot["questions"][1]["options"][0]["option_value"], "ai_tools")
    self.assertEqual(snapshot["questions"][1]["condition"]["source_question_code"], "occupation")
    self.assertLessEqual(self.sql_statement_count, 4)
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_questionnaire_foundation_read_api.QuestionnaireReadServiceTests -v`

Expected: `ModuleNotFoundError` for `questionnaire_read_service`.

- [ ] **Step 3: Implement explicit preload queries and serializers**

```python
def get_version_snapshot(version_id):
    version = (QuestionnaireVersion.query.options(
        selectinload(QuestionnaireVersion.questions).selectinload(QuestionnaireQuestion.options),
        selectinload(QuestionnaireVersion.questions).selectinload(QuestionnaireQuestion.target_condition),
    ).filter_by(id=version_id).first())
    if version is None:
        return None
    return serialize_version(version, include_questions=True)

def serialize_question(question):
    return {"id": question.id, "question_code": question.question_code,
            "title": question.title, "description": question.description,
            "question_type": question.question_type, "required": question.required,
            "sort_order": question.sort_order, "enabled": question.enabled,
            "is_general": question.is_general, "min_selections": question.min_selections,
            "max_selections": question.max_selections, "max_length": question.max_length,
            "options": [serialize_option(item) for item in sorted(question.options, key=lambda item: item.sort_order)],
            "condition": serialize_condition(question.target_condition)}
```

All list functions apply `page` and `per_page` before serialization, cap `per_page` at 100, and order occupations by `sort_order, name`, definitions by `definition_code`, versions by descending `version_number` and questions/options by `sort_order, id`.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `python -m unittest tests.test_questionnaire_foundation_read_api.QuestionnaireReadServiceTests -v`

Expected: ordered snapshot, stable codes and statement-count tests report `ok`.

- [ ] **Step 5: Run model/service regression tests**

Run: `python -m unittest tests.test_questionnaire_foundation_models tests.test_questionnaire_foundation_read_api.QuestionnaireReadServiceTests -v`

Expected: all tests report `OK`.

- [ ] **Step 6: Commit**

```bash
git add backend/questionnaire_models.py backend/questionnaire_read_service.py tests/test_questionnaire_foundation_read_api.py
git commit -m "feat(questionnaire): add foundation read service"
```

### Task 7: Register administrator occupation and definition read APIs

**Files:**
- Create: `backend/questionnaire_admin_read_routes.py`
- Modify: `backend/app.py: imports and registration block near register_v1_routes`
- Modify: `tests/test_questionnaire_foundation_read_api.py: AdminReadApiTests`

**Interfaces:**
- Consumes: `backend/db_pool.py:get_connection`, `questionnaire_read_service` list/detail functions, `flask_jwt_extended`.
- Produces: `register_questionnaire_admin_read_routes(app, get_db_connection) -> None`; GET `/occupations`, `/definitions`, `/definitions/<int:definition_id>`.

- [ ] **Step 1: Write failing API authorization and pagination tests**

```python
def test_admin_can_list_occupations_and_user_cannot(self):
    self.assertEqual(self.get_as("admin", "/api/admin/questionnaire-foundation/occupations").status_code, 200)
    self.assertEqual(self.get_as("user", "/api/admin/questionnaire-foundation/occupations").status_code, 403)

def test_invalid_page_and_unknown_scope_return_safe_400(self):
    response = self.get_as("super_admin", "/api/admin/questionnaire-foundation/definitions?page=0&scope_type=bad")
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.json["code"], 400)
    self.assertNotIn("traceback", response.get_data(as_text=True).lower())
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_questionnaire_foundation_read_api.AdminReadApiTests -v`

Expected: 404 because the route registration function does not exist.

- [ ] **Step 3: Implement route registration and response helpers**

```python
def admin_read_required(get_db_connection):
    def decorate(view):
        @wraps(view)
        @jwt_required()
        def wrapped(*args, **kwargs):
            with get_db_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT role FROM users WHERE username=%s", (get_jwt_identity(),))
                    user = cursor.fetchone()
            if not user or user.get("role") not in ("admin", "super_admin"):
                return api_error("forbidden", 403, 403)
            return view(*args, **kwargs)
        return wrapped
    return decorate

@app.route("/api/admin/questionnaire-foundation/occupations", methods=["GET"])
@admin_read_required(get_db_connection)
def list_occupations_route():
    return api_success(list_occupations(parse_occupation_filters(request.args)))
```

`api_success` and `api_error` emit the existing V1 keys exactly. `parse_page` accepts integers `page >= 1`, `1 <= per_page <= 100`; `parse_boolean` accepts only `true` and `false`; filter parsers reject unrecognised enum values before calling the service. `app.py` imports `questionnaire_models` immediately after the `models` import and calls `register_questionnaire_admin_read_routes(app, get_db_connection)` in the existing route-registration block.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `python -m unittest tests.test_questionnaire_foundation_read_api.AdminReadApiTests -v`

Expected: anonymous 401, `user` 403, `admin`/`super_admin` 200, pagination and safe 400 tests report `ok`.

- [ ] **Step 5: Run authentication and old questionnaire regressions**

Run: `python -m unittest tests.test_auth tests.test_questionnaire_v1_regression tests.test_questionnaire_foundation_read_api.AdminReadApiTests -v`

Expected: all tests report `OK`; no existing endpoint changes status or payload.

- [ ] **Step 6: Commit**

```bash
git add backend/app.py backend/questionnaire_models.py backend/questionnaire_admin_read_routes.py tests/test_questionnaire_foundation_read_api.py
git commit -m "feat(questionnaire): add admin foundation read APIs"
```

### Task 8: Add version-list, version-detail and preview GET APIs

**Files:**
- Modify: `backend/questionnaire_admin_read_routes.py: version routes`
- Modify: `backend/questionnaire_read_service.py: list_versions and get_version_snapshot`
- Modify: `tests/test_questionnaire_foundation_read_api.py: VersionReadApiTests`

**Interfaces:**
- Consumes: Task 6 serializers and Task 7 route helpers.
- Produces: GET `/definitions/<int:definition_id>/versions`, `/versions/<int:version_id>`, `/versions/<int:version_id>/preview`.

- [ ] **Step 1: Write failing version API tests**

```python
def test_version_detail_returns_its_own_snapshot(self):
    response = self.get_as("admin", "/api/admin/questionnaire-foundation/versions/7")
    self.assertEqual(response.status_code, 200)
    data = response.json["data"]
    self.assertEqual(data["version_number"], 2)
    self.assertEqual(data["questions"][0]["question_code"], "occupation")
    self.assertEqual(data["questions"][0]["title"], "Version two occupation title")

def test_missing_version_returns_existing_error_shape(self):
    response = self.get_as("super_admin", "/api/admin/questionnaire-foundation/versions/999999")
    self.assertEqual(response.status_code, 404)
    self.assertEqual(response.json, {"code": 404, "message": "not found", "msg": "not found", "data": {}})
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_questionnaire_foundation_read_api.VersionReadApiTests -v`

Expected: 404 because version routes are not registered.

- [ ] **Step 3: Implement read-only version endpoints**

```python
@app.route("/api/admin/questionnaire-foundation/versions/<int:version_id>", methods=["GET"])
@admin_read_required(get_db_connection)
def get_version_route(version_id):
    snapshot = get_version_snapshot(version_id)
    return api_error("not found", 404, 404) if snapshot is None else api_success(snapshot)

@app.route("/api/admin/questionnaire-foundation/versions/<int:version_id>/preview", methods=["GET"])
@admin_read_required(get_db_connection)
def get_version_preview_route(version_id):
    snapshot = get_version_snapshot(version_id)
    if snapshot is None:
        return api_error("not found", 404, 404)
    snapshot["preview"] = True
    return api_success(snapshot)
```

The routes never load a later version to fill title, option or condition text. They call no mutation service and have no non-GET decorator.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `python -m unittest tests.test_questionnaire_foundation_read_api.VersionReadApiTests -v`

Expected: version list, detail, preview, ordering and 404 tests report `ok`.

- [ ] **Step 5: Run complete read API tests**

Run: `python -m unittest tests.test_questionnaire_foundation_read_api -v`

Expected: all response, authorization, filtering and preview tests report `OK`.

- [ ] **Step 6: Commit**

```bash
git add backend/questionnaire_admin_read_routes.py backend/questionnaire_read_service.py tests/test_questionnaire_foundation_read_api.py
git commit -m "feat(questionnaire): add version read and preview APIs"
```

### Task 9: Verify real-MySQL DDL, constraints and downgrade safety

**Files:**
- Modify: `tests/test_questionnaire_foundation_migration.py: QuestionnaireFoundationMySqlMigrationTests`
- Modify: `backend/scripts/run_sql_migration.py: test database name guard only if required by tests`
- Modify: `backend/sql/migrations/20260719_questionnaire_foundation.up.sql: DDL corrections exposed by integration test`
- Modify: `backend/sql/migrations/20260719_questionnaire_foundation.down.sql: DDL corrections exposed by integration test`

**Interfaces:**
- Consumes: `QUESTIONNAIRE_TEST_DB_NAME`, PyMySQL, Task 1 runner.
- Produces: verified upgrade and rollback contract for the six new tables.

- [ ] **Step 1: Write the failing isolated-MySQL migration test**

```python
@unittest.skipUnless(os.getenv("QUESTIONNAIRE_TEST_DB_NAME"), "QUESTIONNAIRE_TEST_DB_NAME is required for MySQL integration")
def test_upgrade_creates_only_foundation_tables_and_downgrade_keeps_old_tables(self):
    run_migration("upgrade", MIGRATION_NAME, self.connection_factory)
    self.assertEqual(self.table_columns("questionnaire_questions") >= {"question_code", "question_type", "sort_order"}, True)
    self.assertTrue(self.has_unique_key("questionnaire_questions", ("version_id", "question_code")))
    run_migration("downgrade", MIGRATION_NAME, self.connection_factory)
    self.assertTrue(self.table_exists("users"))
    self.assertTrue(self.table_exists("user_profiles"))
    self.assertFalse(self.table_exists("questionnaire_conditions"))
```

- [ ] **Step 2: Run the focused test and confirm the initial failure**

Run: `set QUESTIONNAIRE_TEST_DB_NAME=nav_site_questionnaire_test && python -m unittest tests.test_questionnaire_foundation_migration.QuestionnaireFoundationMySqlMigrationTests -v`

Expected: before final DDL exists, the test fails because `questionnaire_questions` does not exist or lacks the specified unique key.

- [ ] **Step 3: Complete DDL and runner transaction behavior**

The upgrade SQL must use InnoDB, `utf8mb4`, all foreign keys specified in Tasks 2–5, and indexes `idx_occupations_enabled_sort`, `idx_questionnaire_definitions_scope`, `idx_questionnaire_versions_definition_status`, `idx_questionnaire_questions_version_sort`, `idx_questionnaire_options_question_sort`, `idx_questionnaire_conditions_version`. The down file drops only `questionnaire_conditions`, `questionnaire_options`, `questionnaire_questions`, `questionnaire_versions`, `questionnaire_definitions`, `occupations`; it never contains `ALTER TABLE users`, `DROP TABLE users`, `DROP TABLE user_profiles`, `DELETE`, or `UPDATE`.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `set QUESTIONNAIRE_TEST_DB_NAME=nav_site_questionnaire_test && python -m unittest tests.test_questionnaire_foundation_migration.QuestionnaireFoundationMySqlMigrationTests -v`

Expected: upgrade creates all six tables, unique keys exist, and downgrade preserves old tables; test reports `ok`.

- [ ] **Step 5: Run migration and runtime regression tests**

Run: `python -m unittest tests.test_questionnaire_foundation_migration tests.test_db_startup tests.test_backend_runtime_config -v`

Expected: tests without `QUESTIONNAIRE_TEST_DB_NAME` report `OK` with the integration class explicitly skipped; configured CI reports the integration class `ok`; `db.create_all()` remains a runtime helper rather than a migration mechanism.

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/run_sql_migration.py backend/sql/migrations/20260719_questionnaire_foundation.up.sql backend/sql/migrations/20260719_questionnaire_foundation.down.sql tests/test_questionnaire_foundation_migration.py
git commit -m "test(questionnaire): verify foundation migration safety"
```

### Task 10: Lock the first-phase scope with old-system regression coverage

**Files:**
- Create: `tests/test_questionnaire_foundation_regression.py`
- Modify: `tests/test_questionnaire_foundation_read_api.py: method allow-list assertion`

**Interfaces:**
- Consumes: `backend/v1_routes.py`, `backend/app.py`, new read route registration.
- Produces: regression tests proving the foundation has not changed the old questionnaire, recommendation, Authing or existing administrator surface.

- [ ] **Step 1: Write failing scope-regression tests**

```python
def test_foundation_route_module_declares_get_only(self):
    source = (BACKEND_DIR / "questionnaire_admin_read_routes.py").read_text(encoding="utf-8")
    self.assertNotIn('methods=["POST"]', source)
    self.assertNotIn('methods=["PUT"]', source)
    self.assertNotIn('methods=["PATCH"]', source)
    self.assertNotIn('methods=["DELETE"]', source)

def test_legacy_questionnaire_routes_and_fields_remain_present(self):
    source = (BACKEND_DIR / "v1_routes.py").read_text(encoding="utf-8")
    for token in ('"/api/questionnaire"', '"/api/questionnaire/submit"', '"/api/questionnaire/my"', 'questionnaire_completed', 'has_survey'):
        self.assertIn(token, source)
```

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_questionnaire_foundation_regression -v`

Expected: `ModuleNotFoundError` because the regression test module has not been created.

- [ ] **Step 3: Implement the regression suite**

Add tests that import the real Flask application with existing mock strategy, invoke the existing V1 questionnaire regression tests, call the existing recommendation sorter tests, and assert the new route module has exactly the six GET route declarations listed in the API contract. The suite must also assert no foundation file imports `authing_service`, `recommend_service`, or frontend code.

- [ ] **Step 4: Run the focused test and confirm success**

Run: `python -m unittest tests.test_questionnaire_foundation_regression -v`

Expected: GET-only scope and legacy route preservation tests report `ok`.

- [ ] **Step 5: Run the full backend regression suite**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`

Expected: all tests report `OK`; MySQL integration tests are `skipped` only when `QUESTIONNAIRE_TEST_DB_NAME` is absent.

- [ ] **Step 6: Commit**

```bash
git add tests/test_questionnaire_foundation_regression.py tests/test_questionnaire_foundation_read_api.py
git commit -m "test(questionnaire): protect legacy questionnaire behavior"
```

## Plan Self-Review

### Design coverage

Tasks 2–5 cover occupations, definitions, versions, questions, options, conditions, stable codes, foreign keys, status strings and MySQL-safe uniqueness. Tasks 6–8 cover only administrator read services and GET APIs, including pagination, search, filtering, 400/401/403/404 responses, immutable version snapshots and N+1 protection. Tasks 1 and 9 cover the absent formal migration mechanism, upgrade, rollback, table order and old-table protection. Task 10 covers legacy questionnaire, recommendation, authentication and administrator regression protection.

### Scope control

No task defines a write API, version publication, version disablement, rollback action, user draft, automatic save, formal response, history response, deletion request, anonymization, profile compatibility service, frontend page, `/questionnaire` switch, recommendation algorithm change or deployment action. The only mutation planned is schema migration and controlled migration bookkeeping.

### Naming consistency

The plan consistently uses `Occupation`, `QuestionnaireDefinition`, `QuestionnaireVersion`, `QuestionnaireQuestion`, `QuestionnaireOption`, `QuestionnaireCondition`; table names `occupations`, `questionnaire_definitions`, `questionnaire_versions`, `questionnaire_questions`, `questionnaire_options`, `questionnaire_conditions`; route prefix `/api/admin/questionnaire-foundation`; and stable fields `question_code` and `option_value`.
