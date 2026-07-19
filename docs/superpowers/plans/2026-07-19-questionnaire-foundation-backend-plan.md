# Questionnaire Foundation Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立新版问卷后台基础数据模型、迁移和管理员只读查询接口，同时保持现有问卷、认证和推荐功能不变。

**架构：** 新问卷模型使用既有全局 `backend.models.db`，不创建第二套 SQLAlchemy Base。原生 MySQL SQL 由受控运行器执行；读取服务显式注入 session；新问卷管理员路由使用独立支持模块复制已核验的 JWT 身份解析与角色查询规则，不改变任何 V1 路由实现。

**技术栈：** Python 3.14、Flask 3.1.3、Flask-SQLAlchemy 3.1.1、SQLAlchemy 2.0.50、PyMySQL 1.2.0、Flask-JWT-Extended 4.7.4、MySQL、SQLite、`unittest`。

## 全局约束

1. 不改动旧问卷、认证、Authing、推荐、前端、配置或现有 V1 API 的状态码和 JSON。
2. 本阶段只有基础模型、两份 SQL 迁移和管理员 GET 接口；不实施发布、停用、草稿、答卷、匿名化、写接口或种子数据。
3. 稳定键固定为 `question_code`、`option_value`；快照不依赖题目或选项显示文字。
4. 生产结构仅由受版本控制 SQL 修改；全部外键为 `ON DELETE RESTRICT`，表使用 InnoDB、`utf8mb4`。
5. 新路由仅 `admin`、`super_admin` 可读；后端重新查询 `users.role`，不信任前端角色字段。
6. 不记录或返回密码、令牌、连接串、SQL 参数、数据库堆栈或完整结构细节。

---

## 调查结论

- `backend/models.py` 提供唯一的 `db = SQLAlchemy()`；`backend/app.py` 以用户名创建 JWT identity。
- 当前 `v1_routes.py` 的身份查询是 `SELECT * FROM users WHERE username=%s OR email=%s`，两个参数均取 `get_jwt_identity()`；角色仅允许 `admin`、`super_admin`。
- 现有 V1 成功响应已有 `legacy_code`，错误响应没有；本计划不得因此修改 V1。
- 仓库没有 Alembic/Flask-Migrate；`backend/sql/migrations/` 是原生 MySQL SQL 目录。

## 文件结构与创建顺序

| 文件 | 首次动作 | 职责 |
| --- | --- | --- |
| `backend/scripts/run_sql_migration.py` | Task 1 Create | 迁移运行器及 CLI。 |
| `tests/questionnaire_foundation_test_support.py` | Task 1 Create；Task 2/8 Modify | 通用 fixture、后续模型辅助、角色假连接。 |
| `tests/test_questionnaire_foundation_migration.py` | Task 1 Create | 运行器、CLI、MySQL 集成测试。 |
| `backend/questionnaire_constants.py` | Task 2 Create | 枚举和筛选白名单。 |
| `backend/questionnaire_models.py` | Task 2 Create | 六个 ORM 模型和关系。 |
| `backend/questionnaire_validation.py` | Task 2 Create；Task 3–5 Modify | 职业、版本、题目、选项、条件校验。 |
| `tests/test_questionnaire_foundation_models.py` | Task 2 Create | 模型及校验测试。 |
| `backend/sql/migrations/20260719_questionnaire_foundation.up.sql` | Task 6 Create | 六表升级。 |
| `backend/sql/migrations/20260719_questionnaire_foundation.down.sql` | Task 6 Create | 六表反向删除。 |
| `backend/questionnaire_read_service.py` | Task 7 Create | 注入 session 的读取与快照序列化。 |
| `tests/test_questionnaire_foundation_read_api.py` | Task 7 Create；Task 8–10 Modify | 服务、API、鉴权和性能测试。 |
| `backend/questionnaire_admin_support.py` | Task 8 Create | 新问卷响应、参数错误和管理员鉴权。 |
| `backend/questionnaire_admin_read_routes.py` | Task 8 Create | 新问卷 GET 路由。 |
| `backend/app.py` | Task 8 Modify | 导入模型、注册新路由。 |
| `tests/test_questionnaire_foundation_regression.py` | Task 10 Create | 运行时只读与旧功能回归。 |

`backend/v1_routes.py` 不在本计划文件清单中，不得修改。

## 迁移运行器契约

```python
def run_migration(
    direction: str,
    name: str,
    connection_factory: Callable[[], ContextManager[Connection]],
) -> str: ...

def main(argv: Sequence[str] | None = None) -> int: ...
```

返回状态仅为 `applied`、`reverted`、`already_applied`、`not_applied`。名称匹配 `^[0-9]{8}_[a-z0-9_]+$`；只从固定目录读 `<name>.up.sql`、`<name>.down.sql`，拒绝绝对路径、分隔符和路径穿越，且不维护写死的迁移白名单。升级先建/查 `schema_migrations`，全部成功才写记录；回退先查记录，全部成功才删记录。失败调用 `rollback()` 后抛出不含敏感细节的异常。

MySQL DDL 可能隐式提交，运行器不得承诺多条 DDL 完全事务回滚。未登记迁移的任一目标表存在即报“检测到部分迁移状态”，不写成功记录。

`.up.sql` 的首行固定为：

```sql
-- migration-target-tables: occupations,questionnaire_definitions,questionnaire_versions,questionnaire_questions,questionnaire_options,questionnaire_conditions
```

`parse_target_tables(up_sql: str) -> tuple[str, ...]` 仅接受首行此语法；列表非空、顺序稳定、无重复。表名仅字母、数字、下划线；拒绝 schema 前缀、反引号、分号、空白表名、路径字符和 SQL 表达式。`.down.sql` 不重复声明。

回退前运行器用 `.up.sql` 的目标集合查询 `information_schema.KEY_COLUMN_USAGE`，限定 `REFERENCED_TABLE_SCHEMA = DATABASE()`。查询排除 `schema_migrations` 和目标集合本身；只有集合外表对目标表的外键才是外部引用。发现外部引用则安全失败，不执行 `.down.sql`、不删迁移记录、不关闭 `FOREIGN_KEY_CHECKS`。六表之间内部外键不阻止回退。

CLI 仅接受：

```powershell
python backend/scripts/run_sql_migration.py upgrade 20260719_questionnaire_foundation
python backend/scripts/run_sql_migration.py downgrade 20260719_questionnaire_foundation
```

它只接受一个方向与一个迁移名，生产连接只读取现有标准 `MYSQL_`/`DB_` 环境变量，绝不读取 `QUESTIONNAIRE_TEST_DB_*`。成功仅输出迁移名和状态；失败输出安全错误并以非零退出。导入模块不执行迁移，唯一自动入口是：

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

## 当前有效版本规则

持久化字段仅有 `status` 与可空 `current_effective_scope_key`，不存在 `is_current_effective` 列或 ORM 字段。API 只计算：

```python
is_current_effective = version.current_effective_scope_key is not None
```

该键非空时状态必须为 `published`，且等于 `definition.scope_key`；非 `published` 必须为 NULL。已被替代的历史发布版本允许 `status="published"` 且该键为 NULL。发布状态必须有 `published_at`、`published_by_user_id`；非空发布时间也必须有发布人。版本号至少为 1，来源版本不能是自身且必须属于同一定义。

## API 契约

```text
GET /api/admin/questionnaires/occupations
GET /api/admin/questionnaires/definitions
GET /api/admin/questionnaires/definitions/<definition_id>
GET /api/admin/questionnaires/definitions/<definition_id>/versions
GET /api/admin/questionnaires/versions/<version_id>
GET /api/admin/questionnaires/versions/<version_id>/preview
```

新接口的成功和错误各自返回 `code`、`legacy_code`、`message`、`msg`、`data`。新接口的 400、401、403、404 将对应同值业务码显式传给其支持模块；这不是 V1 的全局响应升级。

### Task 1: Add the migration runner, CLI, and model-free support

**Files:** Create `backend/scripts/run_sql_migration.py`、`tests/questionnaire_foundation_test_support.py`、`tests/test_questionnaire_foundation_migration.py`。

**Produces:** 上述 `run_migration`、`parse_target_tables`、`main`；`FakeCursor`、`FakeConnection`、通用 `make_sqlite_app`、`sqlite_session`、`SqlStatementCounter`、`make_jwt_headers`、不依赖问卷模型的基础 TestCase。

- [ ] 写运行器失败测试：非法名称/路径、缺失 SQL、重复升级、未应用回退、rollback、安全错误、部分状态、所有目标声明的合法与非法形式及声明顺序。
- [ ] 写 CLI 测试：参数不足/过多、非法方向/名称均非零；假连接工厂下成功返回 0；导入模块不执行迁移；输出不含密码、连接串、SQL 参数。
- [ ] 实现运行器与 CLI，使用假连接测试而非真实数据库；Task 1 不读取或导入 `questionnaire_models`、`QuestionnaireQuestion`、`QuestionnaireOption`、`QuestionnaireCondition`，也不执行不存在的基础层迁移。
- [ ] `make_sqlite_app()` 只定义通用工厂，使用以下精确配置并在 connect event 执行 `PRAGMA foreign_keys=ON`；此任务不调用 ORM fixture。

```python
from sqlalchemy.pool import StaticPool

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "poolclass": StaticPool,
    "connect_args": {"check_same_thread": False},
}
```
- [ ] 运行 `python -m unittest tests.test_questionnaire_foundation_migration -v` 和既有数据库启动/旧问卷回归。
- [ ] 提交：`feat(questionnaire): add controlled SQL migration runner`。

### Task 2: Add constants, occupation model, validation, and model helpers

**Files:** Create `backend/questionnaire_constants.py`、`backend/questionnaire_models.py`、`backend/questionnaire_validation.py`、`tests/test_questionnaire_foundation_models.py`；Modify `tests/questionnaire_foundation_test_support.py`。不得创建/修改正式迁移 SQL。

定义 `Occupation` 的完整字段：`id`、唯一 `occupation_code`/`name`、`category`、`sort_order`、`enabled`、`new_occupation_policy`、`created_at`、`updated_at`。职业校验验证小写稳定编码、非负排序及 `use_general`/`closed` 策略。

- [ ] 写职业唯一和字段校验失败测试，并用关键字参数构造对象。
- [ ] 用 `from __future__ import annotations` 修改支持文件；在函数体内按真实路径导入模型后加入 `add_occupation`、`add_definition`、`add_version`、`add_question`、`question`、`add_option`、`option`、`add_condition`。每个接收 session 与已声明字段、`add`/`flush`、返回对应实体。
- [ ] 令 `make_sqlite_app()` 在实际 ORM fixture 执行时显式导入 `questionnaire_models`，随后在同一 `models.db.metadata` 上 create_all；每测试按 app context、create_all、测试、rollback、remove、drop_all、退出 context 生命周期清理。
- [ ] 实现职业常量、模型、验证和辅助函数；Task 1 测试仍不调用这些辅助函数。
- [ ] 运行职业/fixture 测试。
- [ ] 提交：`feat(questionnaire): add occupation foundation model`。

### Task 3: Add definition, version model, and state validation

**Files:** Modify `backend/questionnaire_constants.py`、`backend/questionnaire_models.py`、`backend/questionnaire_validation.py`、`tests/test_questionnaire_foundation_models.py`。不得创建/修改正式迁移 SQL。

定义保存 `occupation_id` 的定义，通过关联职业 `occupation_code` 构造 `scope_key`；同一范围仅一个定义。版本包含定义、版本号、状态、可空当前键、来源版本、版本说明、创建人/时间、发布人/时间、更新时间及明确 `foreign_keys` 关系；`current_effective_scope_key` 唯一。

```python
class QuestionnaireDefinition(db.Model):
    __tablename__ = "questionnaire_definitions"
    __table_args__ = (db.UniqueConstraint("scope_key", name="uq_questionnaire_definitions_scope_key"),)
    id = db.Column(db.Integer, primary_key=True)
    definition_code = db.Column(db.String(96), nullable=False, unique=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    scope_type = db.Column(db.String(32), nullable=False)
    scope_key = db.Column(db.String(192), nullable=False)
    occupation_id = db.Column(db.Integer, db.ForeignKey("occupations.id", ondelete="RESTRICT"), nullable=True)
    user_type = db.Column(db.String(32), nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    occupation = db.relationship("Occupation", foreign_keys=[occupation_id])
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])

class QuestionnaireVersion(db.Model):
    __tablename__ = "questionnaire_versions"
    __table_args__ = (db.UniqueConstraint("definition_id", "version_number", name="uq_questionnaire_versions_number"), db.UniqueConstraint("current_effective_scope_key", name="uq_questionnaire_versions_current_scope"))
    id = db.Column(db.Integer, primary_key=True)
    definition_id = db.Column(db.Integer, db.ForeignKey("questionnaire_definitions.id", ondelete="RESTRICT"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="draft")
    current_effective_scope_key = db.Column(db.String(192), nullable=True)
    source_version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_versions.id", ondelete="RESTRICT"), nullable=True)
    version_description = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    published_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    definition = db.relationship("QuestionnaireDefinition", foreign_keys=[definition_id])
    source_version = db.relationship("QuestionnaireVersion", remote_side=[id], foreign_keys=[source_version_id])
    created_by = db.relationship("User", foreign_keys=[created_by_user_id])
    published_by = db.relationship("User", foreign_keys=[published_by_user_id])
    questions = db.relationship("QuestionnaireQuestion", foreign_keys="QuestionnaireQuestion.version_id", order_by="QuestionnaireQuestion.sort_order")
```

```python
def validate_version_state(
    version: QuestionnaireVersion,
    definition: QuestionnaireDefinition,
) -> None: ...
```

- [ ] 写版本号为 0、非法状态、草稿/停用/归档携带有效键、有效键不匹配范围、发布缺发布人/时间、自引用来源的失败测试；测试历史发布版本空有效键合法。
- [ ] 实现范围构造、定义范围验证和上述状态验证；来源版本同定义由关联记录结构校验。
- [ ] 测试定义范围唯一、版本号唯一、有效键唯一与 API 单一计算源。
- [ ] 运行定义/版本目标测试。
- [ ] 运行全部模型测试。
- [ ] 提交：`feat(questionnaire): add definition and version models`。

### Task 4: Add question and option model and validation

**Files:** Modify `backend/questionnaire_constants.py`、`backend/questionnaire_models.py`、`backend/questionnaire_validation.py`、`tests/test_questionnaire_foundation_models.py`。不得创建/修改正式迁移 SQL。

题目含版本、唯一 `question_code`、标题、说明、题型、必填、排序、启用、通用题、选择数量、最大长度、时间字段及 version/options 关系。选项含题目、唯一 `option_value`、显示文字、排序、启用、时间字段及 question 关系。

```python
class QuestionnaireQuestion(db.Model):
    __tablename__ = "questionnaire_questions"
    __table_args__ = (db.UniqueConstraint("version_id", "question_code", name="uq_questionnaire_questions_code"),)
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_versions.id", ondelete="RESTRICT"), nullable=False)
    question_code = db.Column(db.String(96), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    question_type = db.Column(db.String(32), nullable=False)
    required = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    is_general = db.Column(db.Boolean, nullable=False, default=False)
    min_selections = db.Column(db.Integer, nullable=True)
    max_selections = db.Column(db.Integer, nullable=True)
    max_length = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = db.relationship("QuestionnaireVersion", foreign_keys=[version_id])
    options = db.relationship("QuestionnaireOption", foreign_keys="QuestionnaireOption.question_id", order_by="QuestionnaireOption.sort_order")

class QuestionnaireOption(db.Model):
    __tablename__ = "questionnaire_options"
    __table_args__ = (db.UniqueConstraint("question_id", "option_value", name="uq_questionnaire_options_value"),)
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questionnaire_questions.id", ondelete="RESTRICT"), nullable=False)
    option_value = db.Column(db.String(96), nullable=False)
    label = db.Column(db.String(300), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    question = db.relationship("QuestionnaireQuestion", foreign_keys=[question_id])
```

- [ ] 写数据库唯一、字段规则、关联结构规则失败测试。
- [ ] 实现多选必填最小值、可选可为 0、最大值与启用项数、单选禁止选择数量/最大长度、简答正最大长度且无选项、选择题至少一个启用项。
- [ ] 验证标题/标签变化不改变稳定键。
- [ ] 运行题目选项测试。
- [ ] 运行全部模型测试。
- [ ] 提交：`feat(questionnaire): add question and option models`。

### Task 5: Add condition model, relationships, and graph validation

**Files:** Modify `backend/questionnaire_constants.py`、`backend/questionnaire_models.py`、`backend/questionnaire_validation.py`、`tests/test_questionnaire_foundation_models.py`。不得创建/修改正式迁移 SQL。

`QuestionnaireCondition` 含 version、source/target question、expected option、operator、时间字段，所有外键均显式 RESTRICT。为题目增加：

```python
class QuestionnaireCondition(db.Model):
    __tablename__ = "questionnaire_conditions"
    __table_args__ = (db.UniqueConstraint("target_question_id", name="uq_questionnaire_conditions_target"),)
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_versions.id", ondelete="RESTRICT"), nullable=False)
    source_question_id = db.Column(db.Integer, db.ForeignKey("questionnaire_questions.id", ondelete="RESTRICT"), nullable=False)
    target_question_id = db.Column(db.Integer, db.ForeignKey("questionnaire_questions.id", ondelete="RESTRICT"), nullable=False)
    expected_option_id = db.Column(db.Integer, db.ForeignKey("questionnaire_options.id", ondelete="RESTRICT"), nullable=False)
    operator = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = db.relationship("QuestionnaireVersion", foreign_keys=[version_id])
    source_question = db.relationship("QuestionnaireQuestion", foreign_keys=[source_question_id])
    target_question = db.relationship("QuestionnaireQuestion", foreign_keys=[target_question_id])
    expected_option = db.relationship("QuestionnaireOption", foreign_keys=[expected_option_id])
```

```python
source_conditions = db.relationship("QuestionnaireCondition", foreign_keys="QuestionnaireCondition.source_question_id")
target_condition = db.relationship("QuestionnaireCondition", foreign_keys="QuestionnaireCondition.target_question_id", uselist=False)
```

为选项增加 `condition_references = db.relationship("QuestionnaireCondition", foreign_keys="QuestionnaireCondition.expected_option_id")`。条件自身的 source、target、expected option 关系均显式 `foreign_keys`。

```python
def validate_condition(source, target, expected_option, operator) -> None: ...
def validate_condition_graph(questions: Sequence[QuestionnaireQuestion], conditions: Sequence[QuestionnaireCondition]) -> None: ...
```

- [ ] 写同版本、前置排序、自引用、单 target、选项归属/启用、单选 equals、多选 contains、A→B→C→A 的失败测试。
- [ ] 实现单条与图校验，并添加 `configure_mappers()` 不抛异常的 mapper 测试。
- [ ] 测试快照从 `target_condition`、`condition.source_question.question_code`、`condition.target_question.question_code`、`condition.expected_option.option_value` 获取稳定字段。
- [ ] 运行条件/mapper 测试，确保无 `AmbiguousForeignKeysError`。
- [ ] 运行完整模型测试。
- [ ] 提交：`feat(questionnaire): add condition validation`。

### Task 6: Create the complete six-table SQL migration once

**Files:** Create 两份 `20260719_questionnaire_foundation` up/down SQL；Modify `tests/test_questionnaire_foundation_migration.py`。这是唯一正式 SQL 创建任务。

升级顺序为 occupations、definitions、versions、questions、options、conditions，回退完全相反；up 文件以固定声明首行开头。DDL 完整覆盖 Task 2–5 字段、关系、唯一约束、索引、InnoDB、utf8mb4、RESTRICT，且不使用 `CREATE TABLE IF NOT EXISTS`。down 文件只按反向依赖删除六表，不含引用检查、存储过程、动态 SQL 或禁用外键。

- [ ] 写 MySQL 集成测试：六表/列、外键、唯一、索引、字符集、迁移记录、旧表不变、部分状态拒绝。
- [ ] 加入回退测试：六表内部引用仍可回退；第七业务表引用时拒绝；拒绝后记录和六表仍在且 down 未执行；信息 schema 查询限定当前库并排除目标集合。
- [ ] 集成测试只用 `QUESTIONNAIRE_TEST_DB_HOST`、`_PORT`、`_USER`、`_PASSWORD`、`_NAME`，连接后 `SELECT DATABASE()` 必须等于测试名，拒绝空、`nav_site` 和生产库名。
- [ ] 创建完整 SQL 并运行 MySQL 集成测试；生产 CLI 继续使用标准生产环境变量。
- [ ] 运行迁移与运行时回归测试。
- [ ] 提交：`feat(questionnaire): add foundation schema migration`。

### Task 7: Add injected-session read service and serializers

**Files:** Create `backend/questionnaire_read_service.py`、`tests/test_questionnaire_foundation_read_api.py`。

```python
def list_occupations(session: Session, filters: dict) -> dict: ...
def list_definitions(session: Session, filters: dict) -> dict: ...
def get_definition(session: Session, definition_id: int) -> dict | None: ...
def list_versions(session: Session, definition_id: int, filters: dict) -> dict: ...
def get_version_snapshot(session: Session, version_id: int) -> dict | None: ...
```

- [ ] 写筛选、分页、排序、稳定键、None 和条件快照失败测试。
- [ ] 用传入 session 与 `selectinload` 实现服务，使用真实 `target_condition` 和相关 source/option 关系；禁止 `Model.query`。
- [ ] 使用 SQLAlchemy event 计数：详情最多 4–5 条，20 题不新增 20 条；条件关系不产生逐题查询。
- [ ] 运行服务测试。
- [ ] 运行模型与服务回归。
- [ ] 提交：`feat(questionnaire): add foundation read service`。

### Task 8: Add new questionnaire admin support and definition GET APIs

**Files:** Create `backend/questionnaire_admin_support.py`、`backend/questionnaire_admin_read_routes.py`；Modify `backend/app.py`、`tests/questionnaire_foundation_test_support.py`、`tests/test_questionnaire_foundation_read_api.py`。

```python
def register_questionnaire_admin_read_routes(
    app: Flask,
    get_db_connection: Callable[[], ContextManager[Connection]],
) -> None: ...

def questionnaire_admin_required(
    get_db_connection: Callable[[], ContextManager[Connection]],
): ...
```

新鉴权调用 `get_jwt_identity()`，以参数化 `SELECT * FROM users WHERE username=%s OR email=%s` 查询，两参数都为 identity，读取 `users.role`，仅允许 admin/super_admin。新支持模块独立提供新接口响应、参数错误和鉴权；不导入、修改或替换 V1 辅助函数。

```python
class FakeRoleConnectionFactory:
    def __init__(self, roles: dict[str, str]):
        self.roles = roles
        self.identities: list[str] = []

    def __call__(self) -> ContextManager[FakeConnection]:
        """返回支持参数化角色查询的 FakeConnection。"""
```

- [ ] 为支持文件加入 `FakeRoleConnectionFactory(roles: dict[str, str])`：记录 identities，假游标根据两项 JWT 参数返回 user/admin/super_admin/不存在用户；验证参数化查询及两个参数相同。
- [ ] 写匿名 401、不存在用户/普通用户 403、管理员成功、伪造 `role=super_admin` 无效、400/404 以及新响应五键测试；SQLite API 测试不得连接 MySQL。
- [ ] 实现新支持模块与职业列表、定义列表、定义详情 GET；业务查询仍传 `db.session`，鉴权连接职责独立。
- [ ] `app.py` 导入模型并以现有 `get_db_connection` 注册路由；不改任何旧路由。
- [ ] 在注册前后调用至少一个现有 V1 错误接口，断言状态和 JSON 完全相同；单独断言新接口错误含 legacy_code。
- [ ] 提交：`feat(questionnaire): add admin definition read APIs`。

### Task 9: Add version list, detail, preview, and performance tests

**Files:** Modify `backend/questionnaire_admin_read_routes.py`、`backend/questionnaire_read_service.py`、`tests/test_questionnaire_foundation_read_api.py`。

- [ ] 写定义版本列表、详情、预览、404、角色、五键响应、查询计数失败测试。
- [ ] 实现剩余三个 GET 路由；预览仅添加 `preview: true`，不改变任何状态或补读其他版本。
- [ ] 验证列表允许 count+items，详情最多 4–5 条且条件读取没有 N+1。
- [ ] 运行版本和性能测试。
- [ ] 运行全部只读 API 测试。
- [ ] 提交：`feat(questionnaire): add version read APIs`。

### Task 10: Run full regression and protect first-phase scope

**Files:** Create `tests/test_questionnaire_foundation_regression.py`；Modify `tests/test_questionnaire_foundation_read_api.py`。

- [ ] 从真实 Flask `app.url_map` 收集上述前缀，断言 methods 仅 GET、HEAD、OPTIONS。
- [ ] 对每个新端点实际发送 POST、PUT、PATCH、DELETE，断言 405；不以源码字符串检查替代行为测试。
- [ ] 通过正常 unittest discovery 执行既有旧问卷、推荐、认证、管理员测试，不手工调用其他测试类。
- [ ] 运行目标回归测试。
- [ ] 运行 `python -m unittest discover -s tests -p "test_*.py" -v`；无测试库时 MySQL 集成类明确 skipped。
- [ ] 提交：`test(questionnaire): protect foundation scope`。

## 实施前自检

1. 恰有 10 个 Task；`questionnaire_validation.py` 只在 Task 2 Create，后续仅 Modify；两份 SQL 只在 Task 6 Create。
2. Task 1 没有导入未创建的问卷模型，模型辅助只在 Task 2 后加入，迁移模块导入不会执行迁移，CLI 可执行。
3. 目标表声明语法唯一且被解析验证；运行器而非 down SQL 检查外部引用，并排除六表内部引用。
4. `v1_routes.py` 不在文件清单中，旧 V1 状态与 JSON 不变；新鉴权连接可注入，SQLite API 测试不连 MySQL。
5. 非 published 不携带有效范围键；published 有发布人和时间；关系没有多外键歧义；SQLite 使用 StaticPool。
6. 所有新路由只允许 GET、HEAD、OPTIONS；无写接口、发布、草稿、答卷、匿名化、前端、认证、推荐或旧问卷改动。

提交本次文档前运行 `git status --short`、`git diff --stat`、本文件 diff、`git diff --check`；只暂存本文件，检查 cached diff 后提交：

```bash
git commit -m "docs(questionnaire): finalize foundation execution plan"
```

不得暂存认证计划，不得 Push、amend、reset、restore、checkout、clean 或改写历史。
