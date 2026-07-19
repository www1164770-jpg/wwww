# 新版问卷后台基础层实施计划（修订版）

> **实施约束：** 本计划仅覆盖基础模型、受控迁移和管理员只读接口。实施时按任务顺序执行，每个任务先写失败测试、再作最小实现、运行目标与回归测试并独立提交。

**目标：** 在现有 Flask 单体中建立新版问卷的六张基础表、版本化定义模型、受控 SQL 迁移与管理员只读查询；保持旧问卷、认证和推荐行为不变。

**架构：** 新问卷模型继续使用 `backend.models.db`，不创建第二套 declarative base。迁移由原生 SQL 和小型运行器管理；服务层显式注入 SQLAlchemy session；新、旧管理员接口共享经过 JWT 验证后按现有身份解析方式查询 `users.role` 的后端鉴权。所有新增 HTTP 接口仅为 GET。

**技术栈：** Python 3.14、Flask 3.1.3、Flask-SQLAlchemy 3.1.1、SQLAlchemy 2.0.50、PyMySQL 1.2.0、Flask-JWT-Extended 4.7.4、MySQL、`unittest`。

## 全局约束

1. 不改动 `/api/questionnaire`、`/api/questionnaire/submit`、`/api/questionnaire/my`、认证、推荐算法或前台页面。
2. 不实现发布、停用、回滚、草稿、答卷、匿名化、种子数据或任何问卷写接口。
3. 新路由由后端重新读取 `users.role`；仅 `admin`、`super_admin` 可读，匿名与 `user` 不可读。
4. 题目稳定键为 `question_code`，选项稳定键为 `option_value`；快照读取不得依赖显示文字。
5. 生产结构只能经版本化 SQL 改变；不依赖 `db.create_all()` 改动已有生产表。
6. 所有外键均为 `ON DELETE RESTRICT`；使用 InnoDB 与 `utf8mb4`。
7. 日志和响应不得输出密码、令牌、连接串、SQL 参数或数据库堆栈。

## 调查结论

- `backend/models.py` 导出唯一全局 `db = SQLAlchemy()`；新模型必须从此处导入 `db`。
- `backend/app.py` 的 `create_project_token` 与本地登录均以 `identity=user['username']` 创建 JWT。
- `backend/v1_routes.py` 的 `current_user_row` 以 `get_jwt_identity()` 查询 `users`：`WHERE username=%s OR email=%s`；`admin_required` 允许 `admin`、`super_admin`，拒绝时调用 `api_error("forbidden", 403, 403)`。
- 现有 V1 成功响应已经具有 `code`、`legacy_code`、`message`、`msg`、`data`；现有错误响应缺少 `legacy_code`，实施时将以兼容扩展补齐该字段，既有 `code`、`message`、`msg`、`data` 含义不变。
- 仓库没有 Alembic 或 Flask-Migrate。现有 `backend/sql/migrations/` 是原生 MySQL SQL 文件目录。
- 当前测试没有可复用的真实数据库夹具，因此基础层测试需要一份使用同一全局 `models.db` 的 Flask/SQLite 支持文件。

## 确定的文件结构

| 文件 | 动作与首次任务 | 单一职责 |
| --- | --- | --- |
| `backend/scripts/run_sql_migration.py` | Create，Task 1 | 按名称执行升级或回退并维护迁移记录。 |
| `tests/questionnaire_foundation_test_support.py` | Create，Task 1 | Flask/SQLite fixture、假 MySQL 连接、JWT 请求与 SQL 计数支持。 |
| `tests/test_questionnaire_foundation_migration.py` | Create，Task 1 | 运行器与 MySQL 集成迁移测试。 |
| `backend/questionnaire_constants.py` | Create，Task 2 | 枚举、字段长度、筛选白名单。 |
| `backend/questionnaire_models.py` | Create，Task 2 | 六个 ORM 模型、完整字段、关系和数据库约束。 |
| `backend/questionnaire_validation.py` | Create，Task 2 | 职业、题目、选项和条件校验；Task 3–5 只 Modify 此已存在文件。 |
| `tests/test_questionnaire_foundation_models.py` | Create，Task 2 | 实体字段、唯一约束和结构校验。 |
| `backend/sql/migrations/20260719_questionnaire_foundation.up.sql` | Create，Task 6 | 一次性创建六张表。 |
| `backend/sql/migrations/20260719_questionnaire_foundation.down.sql` | Create，Task 6 | 一次性按反向依赖安全回退六张表。 |
| `backend/questionnaire_read_service.py` | Create，Task 7 | session 注入的列表、详情和不可变快照序列化。 |
| `backend/admin_api_support.py` | Create，Task 8 | V1 响应与管理员后端鉴权的最小共享实现。 |
| `backend/questionnaire_admin_read_routes.py` | Create，Task 8 | 长期问卷管理员 GET 路由及参数解析。 |
| `backend/v1_routes.py` | Modify，Task 8 | 导入共享响应/鉴权函数，维持原有路由行为。 |
| `backend/app.py` | Modify，Task 8 | 导入问卷模型并注册只读路由。 |
| `tests/test_questionnaire_foundation_read_api.py` | Create，Task 7 | 服务、接口、鉴权、响应与性能测试。 |
| `tests/test_questionnaire_foundation_regression.py` | Create，Task 10 | 运行时方法限制与旧系统回归保护。 |

## 迁移运行器契约

运行器公开接口固定为：

```python
run_migration(
    direction: str,
    name: str,
    connection_factory: Callable[[], ContextManager[Connection]],
) -> str
```

返回值仅为 `applied`、`reverted`、`already_applied`、`not_applied`。

`name` 必须匹配 `^[0-9]{8}_[a-z0-9_]+$`。运行器将名称解析到固定的 `backend/sql/migrations/`，且仅读取 `<name>.up.sql` 与 `<name>.down.sql`；使用 resolve 后确认父目录仍是该固定目录，拒绝绝对路径、分隔符和路径穿越。运行器不得维护一份写死的允许迁移名称集合，格式、固定目录和文件存在性共同决定是否允许。

升级时先创建 `schema_migrations(name VARCHAR(128) PRIMARY KEY, applied_at DATETIME NOT NULL)`，再查询记录；已有记录返回 `already_applied`。所有升级语句成功后才插入记录。回退时先查询记录；无记录返回 `not_applied`；全部回退语句成功后才删除记录。执行失败必须调用 `rollback()` 并抛出不带连接信息和 SQL 参数的安全异常。

MySQL DDL 可能隐式提交，因此运行器不得宣称多条 DDL 可以完全事务回滚。升级 SQL 首行将携带受解析的目标表声明；当迁移尚未记录、但其中任一目标表已经存在时，运行器拒绝继续并报告“检测到部分迁移状态”，不自动写入成功记录。Task 1 的测试仅验证名称、路径、缺失文件、已应用/未应用、错误回滚和不存在基础层迁移时不执行；Task 6 创建 SQL 后再验证该迁移的目标表检测。

## 当前生效版本的单一来源

`questionnaire_versions` 只保存 `status` 和可空 `current_effective_scope_key`，不保存 `is_current_effective` 列或 ORM 字段。当前版本的该键等于所属定义的 `scope_key`，非当前版本为 `NULL`，数据库对该键建立唯一约束。API 只在序列化时计算：

```python
is_current_effective = version.current_effective_scope_key is not None
```

本阶段仅建立字段和读取规则，不实现发布动作。

## 只读 API 契约

路由前缀固定为 `/api/admin/questionnaires`：

```text
GET /api/admin/questionnaires/occupations
GET /api/admin/questionnaires/definitions
GET /api/admin/questionnaires/definitions/<definition_id>
GET /api/admin/questionnaires/definitions/<definition_id>/versions
GET /api/admin/questionnaires/versions/<version_id>
GET /api/admin/questionnaires/versions/<version_id>/preview
```

每个成功和错误响应都包含 `code`、`legacy_code`、`message`、`msg`、`data`。成功保持 V1 的 `legacy_code: 0`；错误由共享 `api_error` 返回其现有 HTTP/业务 `code` 对应的 `legacy_code`，不另造新的错误码。404 测试必须断言该字段也存在。

## Task 1：迁移运行器及其自身测试

**Files:** Create `backend/scripts/run_sql_migration.py`、`tests/questionnaire_foundation_test_support.py`、`tests/test_questionnaire_foundation_migration.py`。

**接口和实现规则：**

```python
def run_migration(
    direction: str,
    name: str,
    connection_factory: Callable[[], ContextManager[Connection]],
) -> str: ...

def migration_paths(name: str) -> tuple[Path, Path]: ...
def parse_target_tables(up_sql: str) -> tuple[str, ...]: ...
```

`direction` 只接受 `upgrade`、`downgrade`。运行器先验证名称与路径，再读取两个 SQL 文件；缺失文件以安全异常失败。它用参数化查询读取和写入 `schema_migrations`，SQL 脚本按受控语句分隔器顺序执行。错误路径只记录迁移名、方向和安全错误类别。

- [ ] 写失败测试：无效名称、绝对/穿越名称、缺失文件、重复升级、未应用回退、升级失败时 rollback、回退失败时 rollback、未登记且目标表部分存在时拒绝。
- [ ] 写 `FakeCursor`、`FakeConnection`：`executed: list[tuple[str, tuple]]`、`commit() -> None`、`rollback() -> None`、`cursor() -> ContextManager[FakeCursor]`，以可观察方式验证记录写入和删除顺序。
- [ ] 实现运行器；不导入基础层迁移文件，也不在应用导入时执行迁移。
- [ ] 运行 `python -m unittest tests.test_questionnaire_foundation_migration.MigrationRunnerTests -v`。
- [ ] 运行 `python -m unittest tests.test_db_startup tests.test_questionnaire_v1_regression -v`。
- [ ] 提交：`feat(questionnaire): add controlled SQL migration runner`。

支持文件还必须提供完整可复用的测试设施：

```python
def make_sqlite_app() -> Flask:
    """用全局 models.db 建立内存 Flask 应用，不创建第二个 Base。"""

@contextmanager
def sqlite_session() -> Iterator[Session]:
    """进入 app context 后 create_all，yield db.session，最后 rollback、remove、drop_all。"""

class SqlStatementCounter:
    def __enter__(self) -> "SqlStatementCounter": ...
    def __exit__(self, exc_type, exc, traceback) -> None: ...
    @property
    def count(self) -> int: ...

def add_question(session: Session, **fields: object) -> QuestionnaireQuestion:
    """构造、add、flush 并返回题目；调用方传入已声明字段。"""

def question(session: Session, **fields: object) -> QuestionnaireQuestion:
    """测试简写；委托 add_question 并返回已 flush 的题目。"""

def add_option(session: Session, question: QuestionnaireQuestion, **fields: object) -> QuestionnaireOption:
    """以 question.id 写入 question_id，add、flush 并返回选项。"""

def option(session: Session, question: QuestionnaireQuestion, **fields: object) -> QuestionnaireOption:
    """测试简写；委托 add_option 并返回已 flush 的选项。"""

def add_condition(session: Session, **fields: object) -> QuestionnaireCondition:
    """构造、add、flush 并返回条件。"""

class QuestionnaireDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        """进入 sqlite_session，将其返回值赋给 self.session，并启动 SQL 计数器。"""

    def tearDown(self) -> None:
        """停止计数器并退出 sqlite_session，完成 rollback、remove、drop_all。"""

class QuestionnaireApiTestCase(QuestionnaireDatabaseTestCase):
    def get_as(self, username: str, path: str) -> Response:
        """用 make_jwt_headers 发起 GET 并返回真实 Flask 响应。"""

    @property
    def sql_statement_count(self) -> int:
        """返回当前测试持有 SqlStatementCounter 的 count。"""
```

`make_sqlite_app` 配置 `sqlite:///:memory:`、调用同一个 `models.db.init_app(app)`；SQLAlchemy `Engine` connect event 执行 `PRAGMA foreign_keys=ON`。`SqlStatementCounter` 在 session bind 上注册/移除 SQLAlchemy `before_cursor_execute` 监听器。支持文件还定义 `make_jwt_headers(app: Flask, username: str) -> dict[str, str]`，用 `create_access_token(identity=username)` 生成请求头。

## Task 2：常量、职业模型及职业校验

**Files:** Create `backend/questionnaire_constants.py`、`backend/questionnaire_models.py`、`backend/questionnaire_validation.py`、`tests/test_questionnaire_foundation_models.py`；Modify Task 1 支持/迁移测试。不得创建或修改正式迁移 SQL。

定义职业模型及后续模型会使用的用户外键：

```python
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

`NEW_OCCUPATION_POLICIES` 固定为 `use_general`、`closed`。`validate_occupation(occupation: Occupation) -> None` 验证稳定小写编码、非空名称、非负排序和上述策略。

- [ ] 用关键字参数构造职业，测试 ORM 唯一约束和单对象校验；不使用未声明的位置参数。
- [ ] 创建常量、完整职业模型和 `questionnaire_validation.py`，使后续任务只 Modify 后者。
- [ ] 确认模型模块只导入 `models.db`，没有新 declarative base。
- [ ] 运行职业模型目标测试。
- [ ] 运行 Task 1 测试与职业模型测试。
- [ ] 提交：`feat(questionnaire): add occupation foundation model`。

## Task 3：问卷定义和版本模型

**Files:** Modify `backend/questionnaire_constants.py`、`backend/questionnaire_models.py`、`backend/questionnaire_validation.py`、`tests/test_questionnaire_foundation_models.py`。不得创建或修改正式迁移 SQL。

`scope_key` 始终由稳定职业编码构造；模型保存 `occupation_id`，服务通过 `definition.occupation.occupation_code` 构造和验证键。同一 `scope_key` 只允许一个 `QuestionnaireDefinition`，这是正式业务规则而非仅显示约定。

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
    versions = db.relationship("QuestionnaireVersion", foreign_keys="QuestionnaireVersion.definition_id", order_by="QuestionnaireVersion.version_number")

class QuestionnaireVersion(db.Model):
    __tablename__ = "questionnaire_versions"
    __table_args__ = (
        db.UniqueConstraint("definition_id", "version_number", name="uq_questionnaire_versions_number"),
        db.UniqueConstraint("current_effective_scope_key", name="uq_questionnaire_versions_current_scope"),
    )
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

- [ ] 测试范围组合、职业编码构造、范围唯一性、版本号唯一性和可空当前键唯一性。
- [ ] 实现 `build_scope_key(scope_type: str, occupation_code: str | None, user_type: str | None) -> str` 与 `validate_definition_scope(definition: QuestionnaireDefinition) -> None`。
- [ ] 保证 `status`、创建/更新、创建人、发布人、发布时间、来源版本、版本说明和每条关系均已显式声明。
- [ ] 运行定义/版本测试。
- [ ] 运行全部当前模型测试。
- [ ] 提交：`feat(questionnaire): add definition and version models`。

## Task 4：题目和选项模型及校验

**Files:** Modify `backend/questionnaire_constants.py`、`backend/questionnaire_models.py`、`backend/questionnaire_validation.py`、`tests/test_questionnaire_foundation_models.py`。不得创建或修改正式迁移 SQL。

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

数据库层负责版本内题码唯一和题目内选项值唯一。`validate_question_fields(question: QuestionnaireQuestion) -> None` 只验证单对象字段：多选必须有 `min_selections`、`max_selections`；可选多选可为最小值 0，必填多选最小值至少 1，最大值至少 1 且最小值不大于最大值；单选不得设选择数量或 `max_length`；简答只接受正 `max_length` 且不得有选择数量字段。`validate_question_structure(question, options: Sequence[QuestionnaireOption]) -> None` 读取关联记录，要求选择题至少一个启用选项、多选最大值不大于启用选项数、简答没有选项。

- [ ] 为数据库唯一、对象字段和关联记录结构规则分别写失败测试。
- [ ] 实现上述两个验证函数；不得把关联记录规则伪装成数据库约束。
- [ ] 测试标题可变而 `question_code` 稳定、选项显示文字可变而 `option_value` 稳定。
- [ ] 运行题目/选项目标测试。
- [ ] 运行全部模型测试。
- [ ] 提交：`feat(questionnaire): add question and option models`。

## Task 5：条件模型、单条条件校验和条件图校验

**Files:** Modify `backend/questionnaire_constants.py`、`backend/questionnaire_models.py`、`backend/questionnaire_validation.py`、`tests/test_questionnaire_foundation_models.py`。不得创建或修改正式迁移 SQL。

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

接口固定为：

```python
def validate_condition(source, target, expected_option, operator) -> None: ...
def validate_condition_graph(
    questions: Sequence[QuestionnaireQuestion],
    conditions: Sequence[QuestionnaireCondition],
) -> None: ...
```

单条验证要求 source、target、选项属于同一版本；source 排序小于 target；不得自引用；`equals` 只用于单选，`contains` 只用于多选；期望选项属于 source、启用且在当前版本可用。图验证要求每个 target 最多一条条件且无环。测试真实构造 A → B、B → C、C → A 并断言拒绝。

- [ ] 写类型、版本、排序、期望选项、单 target 与循环的失败测试。
- [ ] 实现单条与 DFS/颜色标记图验证函数。
- [ ] 测试 `source_question_code`、`target_question_code` 和期望 `option_value` 的序列化来源均为稳定键。
- [ ] 运行条件目标测试。
- [ ] 运行完整模型测试。
- [ ] 提交：`feat(questionnaire): add condition validation`。

## Task 6：一次性完成六张表的完整 SQL 升级与回退迁移

**Files:** Create `backend/sql/migrations/20260719_questionnaire_foundation.up.sql`、`backend/sql/migrations/20260719_questionnaire_foundation.down.sql`；Modify `tests/test_questionnaire_foundation_migration.py`。这是唯一创建正式迁移 SQL 的任务。

升级 SQL 首行声明六个目标表。创建顺序严格为 `occupations`、`questionnaire_definitions`、`questionnaire_versions`、`questionnaire_questions`、`questionnaire_options`、`questionnaire_conditions`；回退顺序完全相反。DDL 包含 Task 2–5 中列出的每一个字段、外键、唯一约束、索引、InnoDB 和 `utf8mb4`，并将所有外键定义为 `ON DELETE RESTRICT`。不得使用 `CREATE TABLE IF NOT EXISTS`。

回退 SQL 在删除前通过 information schema 检查是否有后续业务表引用六张核心表；发现引用即安全失败，不关闭外键检查。它只删除这六张新表，不修改旧表。

- [ ] 写 MySQL 集成测试：六表/列、外键、唯一约束、索引、字符集、迁移记录写入、回退记录删除、旧表不变、部分迁移状态拒绝。
- [ ] 创建完整 up/down SQL；SQL 内没有旧问卷字段变更。
- [ ] 为集成测试只读取 `QUESTIONNAIRE_TEST_DB_HOST`、`QUESTIONNAIRE_TEST_DB_PORT`、`QUESTIONNAIRE_TEST_DB_USER`、`QUESTIONNAIRE_TEST_DB_PASSWORD`、`QUESTIONNAIRE_TEST_DB_NAME`。
- [ ] 连上后执行 `SELECT DATABASE()`，确认等于测试名称；拒绝空名、`nav_site` 和等于当前生产数据库名。生产运行器仍读取标准 `MYSQL_`/`DB_` 配置，不受测试保护影响。
- [ ] 在 PowerShell 设置测试变量并执行：

```powershell
$env:QUESTIONNAIRE_TEST_DB_NAME="nav_site_questionnaire_test"
python -m unittest tests.test_questionnaire_foundation_migration.QuestionnaireFoundationMySqlMigrationTests -v
```

- [ ] 提交：`feat(questionnaire): add foundation schema migration`。

## Task 7：只读服务和序列化

**Files:** Create `backend/questionnaire_read_service.py`、`tests/test_questionnaire_foundation_read_api.py`。

服务接口固定并全部显式注入 session：

```python
def list_occupations(session: Session, filters: dict) -> dict: ...
def list_definitions(session: Session, filters: dict) -> dict: ...
def get_definition(session: Session, definition_id: int) -> dict | None: ...
def list_versions(session: Session, definition_id: int, filters: dict) -> dict: ...
def get_version_snapshot(session: Session, version_id: int) -> dict | None: ...
```

生产路由传入 `db.session`；测试传入 Task 1 的隔离 SQLite session。服务不得调用 `Model.query`。快照使用 selectinload 预加载版本、题目、选项和条件，按版本/题目/选项排序关系稳定输出；`is_current_effective` 只由可空有效范围键计算。

- [ ] 写服务序列化、筛选、排序、稳定编码和不存在返回 `None` 的失败测试。
- [ ] 实现分页（count 加 items 合法）、白名单筛选与服务端预加载。
- [ ] 使用 `SqlStatementCounter` 测试版本详情至多 4–5 条查询：版本、题目、选项、条件；增加 20 道题后不增加 20 条查询。
- [ ] 运行服务目标测试。
- [ ] 运行模型与服务测试。
- [ ] 提交：`feat(questionnaire): add foundation read service`。

## Task 8：职业与问卷定义只读 API

**Files:** Create `backend/admin_api_support.py`、`backend/questionnaire_admin_read_routes.py`；Modify `backend/v1_routes.py`、`backend/app.py`、`tests/test_questionnaire_foundation_read_api.py`。

共享模块采用已调查的真实 V1 逻辑：JWT identity 来自 `get_jwt_identity()`，通过 `SELECT * FROM users WHERE username=%s OR email=%s` 查找用户，角色不在 `admin`、`super_admin` 则返回 `api_error("forbidden", 403, 403)`。`v1_routes.py` 将现有 `api_success`、`api_error`、`current_user_row`、`admin_required` 抽到此最小模块并导入，确保旧接口与新接口共用同一鉴权和响应规则。`api_error` 为所有错误加 `legacy_code`，保留既有其余字段和值。

创建职业、定义列表和定义详情三个 GET 路由；路由传入 `db.session` 至服务，不实现任何写操作。

- [ ] 写匿名 401、普通用户 403、管理员/超级管理员 200、参数 400 与 404 响应形状的失败测试。
- [ ] 实现共享模块、参数解析和三个接口；所有成功/错误结构均有五个约定键。
- [ ] 修改 `app.py` 以导入模型并注册路由；不移动既有路由。
- [ ] 运行接口目标测试和既有 V1 管理员接口回归测试。
- [ ] 运行认证和旧问卷回归。
- [ ] 提交：`feat(questionnaire): add admin definition read APIs`。

## Task 9：版本列表、详情、预览及查询性能测试

**Files:** Modify `backend/questionnaire_admin_read_routes.py`、`backend/questionnaire_read_service.py`、`tests/test_questionnaire_foundation_read_api.py`。

实现剩余三个长期路径：定义版本列表、版本详情、版本预览。预览只在详情快照外添加 `preview: true`，不读取其他版本补全标题/选项/条件。不存在对象返回带 `legacy_code` 的 404。所有六个路径只注册 GET。

- [ ] 写版本分页、快照顺序、预览、404、角色和完整响应结构失败测试。
- [ ] 实现三条 GET 路由；不得引入写服务或状态改变。
- [ ] 用 SQLAlchemy event 计数验证列表允许 count+items，详情最多 4–5 条且 20 题不产生线性查询。
- [ ] 运行版本和性能目标测试。
- [ ] 运行所有只读 API 测试。
- [ ] 提交：`feat(questionnaire): add version read APIs`。

## Task 10：全量回归与第一阶段范围保护

**Files:** Create `tests/test_questionnaire_foundation_regression.py`；Modify `tests/test_questionnaire_foundation_read_api.py`。

回归测试从真实 Flask `app.url_map` 收集 `/api/admin/questionnaires` 规则，断言其 methods 仅含 GET、HEAD、OPTIONS；对每个端点实际发送 POST、PUT、PATCH、DELETE 并断言 405。不得以搜索装饰器字符串代替运行时行为测试，也不得在新测试中手工调用其他测试类。

- [ ] 写 app.url_map 方法集合和四类非 GET 请求的失败测试。
- [ ] 覆盖真实旧问卷接口回归、现有推荐测试、现有管理员鉴权测试，并通过正常 unittest 发现机制运行。
- [ ] 可保留少量架构依赖检查，但它们不能替代行为测试。
- [ ] 运行 `python -m unittest tests.test_questionnaire_foundation_regression -v`。
- [ ] 运行 `python -m unittest discover -s tests -p "test_*.py" -v`；未配置测试库时 MySQL 集成类明确 skipped。
- [ ] 提交：`test(questionnaire): protect foundation scope`。

## 实施前自检清单

1. 恰有 10 个 Task，顺序为运行器、职业、定义版本、题选项、条件、SQL、服务、职业定义 API、版本 API、回归。
2. `questionnaire_validation.py` 仅在 Task 2 Create，Task 3–5 Modify。
3. 两份正式 SQL 只在 Task 6 Create；Task 1 不运行尚不存在的基础层迁移。
4. 运行器、记录、重复处理、MySQL DDL 限制和部分状态拒绝均已说明。
5. 没有第二个当前生效布尔字段或双重状态来源。
6. 模型示例包含完整生命周期字段、人员外键、发布信息、来源版本、关系与 RESTRICT。
7. 多选、简答、条件图、可注入 session、fixture、JWT、查询计数和 MySQL 专用连接均有确定实现。
8. 新旧管理员接口复用真实身份查询和角色判定；所有错误含 `legacy_code`。
9. 仅有 `/api/admin/questionnaires` 长期 GET 路径；没有本阶段外的写功能。

实施前还应对本计划运行预置的占位语检查，预期没有匹配；检查命令不写入本计划，以免检查命令本身成为匹配项。

## 本次文档提交检查

本次只允许改动本计划文件。提交前运行：

```bash
git status --short
git diff --stat
git diff -- docs/superpowers/plans/2026-07-19-questionnaire-foundation-backend-plan.md
git diff --check
git add docs/superpowers/plans/2026-07-19-questionnaire-foundation-backend-plan.md
git diff --cached --check
git diff --cached --stat
git commit -m "docs(questionnaire): harden foundation implementation plan"
git status -sb
git log -5 --oneline
git show --stat --oneline HEAD
```

不得暂存 `docs/superpowers/plans/2026-07-13-authentication-closure-plan.md`，不得 Push、amend、reset、restore、clean 或修改历史提交。
