# 智汇网站爬虫系统设计

**日期：** 2026-07-30  
**状态：** 已确认  
**实施边界：** 本轮只实现 Phase 1 基础设施；本文描述完整系统的稳定边界。

## 1. 目标与非目标

系统目标是在 Windows 单机上，以公开、合规、可恢复的方式发现并处理网站，首期形成约 100,000 个公开网站的候选库。夜间窗口为每日 01:00–05:00，目标处理量为每晚 3,000 个网站；05:00 后不再租赁新任务，已经租赁的任务允许在租约范围内安全结束。架构必须能在不改变任务协议和数据库语义的前提下迁移到 Linux 或多主机部署。

系统目标还包括：

- 以 MySQL 中的持久任务队列替代进程内队列，支持崩溃恢复、重试、死信和审计。
- 以规则优先、模型补充的方式提取、归类和评估网站。
- 保存原文证据，生成中文摘要与标签，并保留原始语言信息。
- 高可信网站自动批准，中风险网站进入管理员审核，高风险网站自动拒绝并保存原因。
- 只有审核通过的数据才可通过 Outbox 同步至现有正式数据库。

本系统不以绕过登录、验证码、Cloudflare 挑战、付费墙或访问控制为目标；不抓取非公开数据，不进行无限深度递归，也不把现有正式数据库当作爬虫工作库。Phase 1 不实现实际抓取、内容分析、风险判定、管理员界面、正式库同步或夜间自动注册。

## 2. 合规与安全边界

每次抓取前必须执行以下检查：

1. 仅处理公开 HTTP/HTTPS 资源。
2. 遵守 robots.txt；无法可靠解析时采用保守策略。
3. 每域名并发上限为 1，请求间隔随机 1–3 秒；全局 Scrapy 并发上限为 24，Playwright 并发上限为 2。
4. 默认只抓首页和最多 5 个关键页面；关键页面只能来自同站受控链接集合。
5. 不尝试提交登录表单、解验证码、绕过挑战、访问付费内容或模拟已认证用户。
6. 严格排除成人、赌博、毒品、武器、诈骗、钓鱼、恶意软件、盗版下载和仇恨极端内容。
7. 对 DNS 重绑定、内网地址、环回地址、链路本地地址、云元数据地址和非 HTTP 协议执行 SSRF 阻断。
8. 日志、任务错误和审计记录不得包含 Authorization、Cookie、数据库密码、完整正文或个人敏感信息。

抓取响应设大小、类型和时限上限。重定向后的每一跳重新执行协议、主机和地址安全检查。风险过滤结果必须包含机器可读错误码、规则版本和最小必要证据，不能保存违禁内容的完整副本。

## 3. 单机模块化总体架构

系统采用同一仓库内的独立 Python 包 `backend/crawler/`，但不导入现有 Flask 应用的数据库对象，也不在 Flask 应用启动时创建爬虫 engine。所有模块通过数据库任务、稳定 UID 和 JSON 载荷协作：

```text
Windows Scheduler
       |
       v
Scheduler -> Discovery -> Fetch(Scrapy -> optional Playwright)
       |          |                 |
       +------ MySQL task queue <---+
                         |
                         v
                 Analysis -> Review
                                  |
                                  v
                          Outbox Worker
                                  |
                                  v
                      existing production API/DB
```

单机部署可由多个独立进程承担 scheduler、discovery、fetch、analysis、review 和 outbox 职责。进程不依赖本地内存保存唯一状态；任务、租约、心跳和 run 状态均写入 `zhihui_crawler`。文件系统只保存图标、日志和可安全重建的临时文件。

Phase 1 使用 `backend/crawler/observability/` 而不是 `backend/crawler/logging/`，避免包名遮蔽 Python 标准库 `logging`。

## 4. 模块职责

### Scheduler

创建唯一 `crawl_run`，根据 01:00–05:00 窗口、目标量和系统设置投放任务；05:00 设置 `stop_requested`。它只阻止新任务租赁，不杀死已经工作的进程。Scheduler 负责重试到期任务、恢复过期租约和结束 run。

### Discovery

通过公开目录、RSS、Atom、Sitemap、Common Crawl 公共索引、公开名录和已批准站点外链产生候选 URL。Provider 采用接口化设计，商业搜索 Provider 可在不改变队列协议的情况下加入，但默认禁用。

### Scrapy Fetch

执行 robots、速率、域名并发、响应大小、重定向和页面数量限制。它输出规范化抓取快照，不直接写正式站点表。

### Playwright Fetch

仅当静态抓取得不到有效正文，且规则允许时作为降级路径。该模块共享 URL 安全边界，限制并发为 2，并设进程、页面和浏览器资源上限。

### Analysis

先运行确定性规则：元数据提取、语言识别、类别候选、内容质量和安全信号。规则置信度不足时才调用本地 Ollama。每个结果保存规则版本、模型标识、输入证据摘要和置信度。

### Review

把候选站点转换为 `approved`、`review_required` 或 `rejected`。高可信自动批准，中风险进入管理员队列，高风险自动拒绝。人工操作只允许现有管理员角色，并产生不可变审计事件。

### Outbox Worker

租赁已准备好的 Outbox 事件，调用受控同步适配器写入正式系统；不共享正式库连接，不跨两个数据库制造伪原子事务。事件以 `event_uid` 幂等，成功后标记 processed，失败按退避重试。

## 5. `zhihui_crawler` 独立数据库边界

爬虫使用独立 MySQL 数据库，默认且正式允许的库名精确为 `zhihui_crawler`。连接只来自 `CRAWLER_DATABASE_URL`。以下行为被禁止：

- 从现有 `MYSQL_*`、`DB_*` 或 Flask `SQLALCHEMY_DATABASE_URI` 推导爬虫连接。
- 在 `backend/app.py` 导入时验证、连接或迁移爬虫数据库。
- 在正式项目库中创建爬虫表。
- 自动创建数据库、删除未知表、清空表、自动 seed 或创建管理员。

测试 MySQL 数据库名称必须包含 `test`；未显式设置 `CRAWLER_TEST_DATABASE_URL` 时集成测试跳过。SQLite 只用于事务语义单元测试，不代表生产存储。

## 6. 正式数据库同步边界

正式数据库写入只发生在 Phase 4 的 Outbox 消费适配器中。审核通过事务在 `zhihui_crawler` 内同时写审核状态和 outbox 事件，确保“批准”与“待同步”不可分离。Outbox Worker：

- 用 `event_uid` 作为正式端幂等键。
- 只发送字段白名单，不发送抓取正文、Cookie 或内部风险证据。
- 根据正式端响应区分成功、可重试失败和永久失败。
- 不直接复用 `db_pool.py`，不在一个本地事务中同时操作两个数据库。

Phase 1 只实现 outbox 表和队列原语，不实现任何正式库连接或同步业务。

## 7. 任务队列与租约模型

任务状态集中定义为 `pending`、`leased`、`completed`、`failed`、`dead`、`cancelled`。合法转换为：

```text
pending -> leased
pending -> cancelled
leased  -> completed
leased  -> failed
leased  -> pending     (expired lease recovery)
failed  -> pending     (retry becomes due)
failed  -> dead
failed  -> cancelled
```

`completed`、`dead` 和 `cancelled` 是终态，必须显式创建新任务才能再次处理目标。

租赁在单个 MySQL 事务中以候选查询、`FOR UPDATE SKIP LOCKED`、状态更新和计数更新完成。排序规则为：

1. `priority` 数值越小优先级越高；
2. `available_at` 早者优先；
3. `created_at` 早者优先；
4. `id` 作为稳定并列顺序。

批量 `limit` 为 1–100。租赁只选择 `pending` 且 `available_at <= now` 的任务。属于 `stop_requested` 或终态 run 的新任务不可租赁；已经 leased 的任务仍可完成。

失败或过期租约增加 `attempt_count`。未到上限时使用指数退避和小幅随机抖动；到上限转为 `dead`。恢复动作只选择仍为 leased 且租约确实过期的行，因此重复执行不重复增加次数。

## 8. 数据表总体设计

### Phase 1 表

`crawl_runs`

- 主键 `id`：BIGINT；SQLite 测试使用 INTEGER 变体。
- `run_uid` 唯一。
- 状态、调度/开始/停止请求/完成时间。
- 目标、租赁、完成、失败计数。
- 创建和更新时间。
- 索引：唯一 `run_uid`，以及 `(status, scheduled_for)`。

`crawl_tasks`

- 主键 `id`、唯一 `task_uid`、可空 `run_id` 外键。
- `task_type`、规范化 `target`、稳定 `target_hash`。
- `dedupe_key` 保存稳定去重代际，`active_dedupe_key` 在活跃状态保存同值，在终态置空。
- JSON `payload_json`、优先级、状态、尝试次数和最大次数。
- 可用、租赁、完成时间，worker、截断错误码和错误信息。
- 索引：唯一 `(task_type, active_dedupe_key)`；租赁候选 `(status, available_at, priority, created_at)`；`leased_until`；`run_id`。

MySQL 与 SQLite 都允许唯一索引中出现多个 NULL。因此 active 状态防重，终态置 NULL 后可创建相同目标的新代任务；刷新任务也可使用不同 `task_type` 或显式代际 `dedupe_key`。这避免了永久禁止同一 URL 再抓取。

`worker_heartbeats`

- 主键、唯一 `worker_id`、worker 类型、PID、hostname。
- 存储状态、当前任务 UID、启动和最后活动时间、脱敏 JSON 元数据。
- 索引：唯一 `worker_id`，以及 `(status, last_seen_at)`。

`crawler_settings`

- `setting_key` 为主键，等价于唯一约束。
- 值、值类型、更新人和时间戳。
- 不存储数据库 URL、密码、token 或 Cookie；秘密只由环境或操作系统秘密管理提供。

`outbox_events`

- 主键、唯一 `event_uid`、聚合类型/UID、事件类型和 JSON payload。
- 状态、尝试次数、可用和租赁时间、worker、截断错误、处理时间和时间戳。
- 索引：唯一 `event_uid`，以及 `(status, available_at, created_at)` 和 `leased_until`。

### 后续阶段表族

Phase 2 增加 discovery sources、URL observations、fetch snapshots 和 candidate sites；Phase 3 增加 analysis results、risk decisions 和 icon assets；Phase 4 增加 review decisions、audit entries 和 sync receipts。每张业务表使用稳定 UID，原始快照与派生分析分离，避免模型升级覆盖证据。

## 9. URL 与域名规范化

URL 规范化分两层：

- Phase 1 队列基础规范化：去首尾空白；只对 HTTP/HTTPS 小写 scheme 和 hostname；移除 fragment；移除默认 80/443 端口；空 path 规范为 `/`；保留 path 与 query；输出 SHA-256 `target_hash`。
- Phase 2 抓取规范化：IDNA 主机、点段处理、百分号编码一致化、查询参数排序/追踪参数策略、canonical 链接评估和站点级归并。

规范化函数必须是纯函数并版本化。原始发现 URL 与规范 URL 分开保存。域名键采用规范 hostname 与有效端口，不把不同 scheme 或非默认端口错误合并。任何 DNS 解析结果都经过公网地址验证。

## 10. 抓取快照与候选网站生命周期

生命周期为：

```text
discovered -> fetch_pending -> fetched -> analysis_pending
-> approved | review_required | rejected
-> outbox_pending -> synchronized
```

抓取快照不可原地覆盖：每次抓取生成新 snapshot UID，包含响应元数据、内容哈希、正文对象位置、抓取器版本和合规决策。候选站点保存当前快照引用和生命周期状态。相同内容哈希可避免重复分析，但不会删除历史证据。

失败细分为临时网络、永久 HTTP、robots 拒绝、安全拒绝、内容过大、解析失败和资源超限。只有可重试类别重新入队。

## 11. 规则分析与 Ollama 降级策略

Analysis 首先运行确定性规则并生成可解释分值。规则覆盖标题/描述、结构化数据、导航语义、内容量、站点类别、语言、安全信号和质量信号。高置信度结果不调用模型。

当关键字段缺失、类别冲突或置信度低于配置阈值时，构造最小化、截断和清洗后的模型输入调用本地 Ollama。模型输出必须通过 JSON schema 校验；超时、不可用、显存不足或格式错误时保留规则结果并标记 `model_unavailable`，不会阻塞整条流水线。8GB NVIDIA 显存是默认资源预算，模型与上下文长度由配置固定并记录版本。

## 12. 多语言与中文摘要策略

系统保存原始语言、检测语言、检测置信度和原文证据。分析输出统一包含中文摘要与中文标签，同时允许保存原语言标题和摘要。策略为：

- 中文原文直接生成精简中文摘要。
- 非中文原文先提取事实，再在受控长度内生成中文摘要。
- 规则能完成的语言、标题和类别不调用模型。
- 模型不可用时使用结构化元数据和截断文本生成确定性回退摘要，不伪造翻译质量。
- 摘要保存生成方式、规则/模型版本和时间，后续可重算。

## 13. favicon/logo 文件存储

图标根目录由 `CRAWLER_ICON_ROOT` 指定，默认解析为仓库根下 `backend/data/crawler/icons/`。文件名使用内容 SHA-256，不使用用户提供文件名；目录按哈希前两字节分片。数据库保存内容哈希、MIME、尺寸、来源 URL、获取时间和相对路径。

只接受白名单图像类型，限制响应大小和解码尺寸，拒绝 SVG 中的活动内容风险。写入采用临时文件、校验后原子重命名。图标是可重建资源，不进入 Git；README 或 `.gitkeep` 可保留。

## 14. 严格风险过滤

风险判定分三道门：

1. 抓取前：URL、DNS、协议、robots 和访问控制检查。
2. 抓取后：重定向、MIME、内容大小、恶意下载、违禁类别和安全信号检查。
3. 发布前：规则与模型风险评分、来源可信度、人工审核门槛。

高风险直接拒绝，记录规则码、版本、置信度和最小证据哈希；中风险进入人工审核；高可信且无硬拒绝规则才自动批准。模型不能覆盖硬拒绝规则。规则更新不会静默改写旧结论，而是创建新分析版本。

## 15. 管理员审核与审计

Phase 4 管理接口复用现有数据库支持的管理员身份和角色判断，但使用专用 API 访问 `zhihui_crawler`，不允许普通用户访问。所有查看敏感证据、批准、拒绝、重跑和同步动作记录：

- actor 稳定标识与角色；
- action、对象 UID、前后状态；
- 原因码与人工备注摘要；
- 请求关联 ID、时间和来源；
- 使用的规则/模型版本。

审计记录只追加，不由普通管理操作删除。响应字段使用白名单，原始正文按最小权限和保留期提供。

## 16. Windows 01:00–05:00 调度

Phase 5 使用 Windows 任务计划程序调用固定的 Python 模块入口，而不是依赖终端当前目录。01:00 启动 controller，controller 创建或恢复当日 run；05:00 的独立 stop 任务请求 run 停止，以便即使 controller 异常也能关闭新租赁。

脚本从自身位置解析仓库根，激活由操作员配置的解释器路径，不把私人绝对路径写入仓库。任务计划定义运行用户、工作目录、失败重启策略和最大运行时。stop_requested 后 worker 完成已有租约并停止获取新任务。PID 文件仅用于诊断，正确性依赖数据库心跳和租约。

## 17. 配置与秘密管理

Phase 1 配置项：

| 变量 | 默认值 | 规则 |
| --- | --- | --- |
| `CRAWLER_DATABASE_URL` | 无 | 仅爬虫 CLI 必需，不回退到正式库 |
| `CRAWLER_ICON_ROOT` | `backend/data/crawler/icons` | 相对路径按仓库根解析 |
| `CRAWLER_LOG_ROOT` | `backend/data/crawler/logs` | 相对路径按仓库根解析 |
| `CRAWLER_WORKER_ID` | `hostname-pid` | 可显式覆盖 |
| `CRAWLER_LEASE_SECONDS` | `300` | 正整数 |
| `CRAWLER_MAX_ATTEMPTS` | `3` | 正整数 |
| `CRAWLER_NIGHTLY_TARGET` | `3000` | 正整数 |
| `CRAWLER_START_TIME` | `01:00` | 24 小时 `HH:MM` |
| `CRAWLER_STOP_TIME` | `05:00` | 晚于开始时间 |

真实数据库 URL、密码、token 和 Cookie 不写入 Git、crawler_settings、CLI 输出或日志。`.env.example` 只写变量名、无秘密示例和说明；真实 `.env` 不读取、不覆盖、不展示。生产优先使用操作系统环境或秘密管理器注入。

## 18. 日志、指标与故障恢复

爬虫日志使用单行 JSON，至少包含 `timestamp`、`level`、`component`、`event`、`worker_id`、`run_uid`、`task_uid`、`duration_ms`、`error_code`。敏感键递归脱敏，数据库 URL 隐藏密码，错误消息截断且不保存完整正文。

核心指标包括任务入队/租赁/完成/失败/死信计数，租赁等待时间，处理时长，按错误码失败率，worker 心跳年龄，run 完成率，outbox 积压和日志写入失败。Phase 1 CLI `status --json` 提供数据库状态快照；后续可输出 Prometheus 或 Windows 性能数据。

故障恢复依靠：

- 过期租约扫描与幂等恢复；
- worker 心跳的 online/stale/stopped 派生状态；
- event/task 稳定 UID；
- 重试上限、指数退避和死信；
- run stop_requested 与缓存计数的数据库事务更新；
- Outbox 消除跨库同步窗口。

文件日志不可写时回退 stderr，不能导致队列事务失败。

## 19. 数据保留与清理

建议保留策略：

- crawl task/run 元数据：180 天；终态汇总保留 1 年。
- 抓取原文和快照：90 天；审核或安全争议证据按审计策略延长。
- 分析结果与审核审计：至少 1 年。
- processed outbox：90 天；dead outbox 保留到人工处置后 180 天。
- JSON 日志：30 天滚动；错误汇总指标保留 180 天。
- 未引用图标和临时文件：校验无数据库引用后 30 天清理。

清理任务只删除满足保留期且处于明确终态的数据，分批执行并记录数量。它不得级联删除审计或尚未处理的 outbox。Phase 5 才提供清理命令和运行手册。

## 20. 分阶段实施

### Phase 1：基础设施

建立独立包、配置、独立数据库模型与迁移、MySQL 队列、租约恢复、worker 心跳、crawl run、outbox 原语、CLI 和结构化日志。只提供 smoke 原语，不启动实际 worker。

### Phase 2：静态抓取 MVP

实现免费发现 Provider、RSS/Atom/Sitemap、Scrapy、robots、页面限制、完整 URL 规范化、不可变快照和候选站点生命周期。

### Phase 3：分析、安全与资源

实现规则提取、语言识别、中文摘要、Ollama 降级、风险评分、严格过滤和 favicon/logo 缓存。

### Phase 4：审核与正式库同步

实现管理员 API/页面、人工审核、审计、Outbox 业务事件和正式系统幂等同步。

### Phase 5：动态抓取与夜间运行

实现 Playwright 按需降级、资源控制、Windows 任务计划脚本、01:00–05:00 安全启停、监控、清理和运维手册。

## 21. 测试策略

测试分层：

- 纯单元测试：配置解析、状态转换、规范化、退避和日志脱敏。
- SQLite 事务测试：模型约束、入队幂等、租赁语义、失败/恢复、run、heartbeat 和 outbox；测试数据库每例隔离。
- MySQL SQL 编译测试：验证候选查询生成 `FOR UPDATE SKIP LOCKED`、索引与 MySQL DDL 结构。
- MySQL 集成测试：仅在显式 `CRAWLER_TEST_DATABASE_URL` 且库名包含 `test` 时运行，覆盖两个连接并发租赁、唯一约束和迁移。
- CLI 测试：缺配置、数据库错误、JSON 输出、秘密不泄露和“数据库错误”不等同“空结果”。
- 回归测试：现有 Flask 启动、职业推荐、API 基址、前端构建和收藏脚本。
- Phase 2–5 增加 robots、SSRF、限速、抓取夹具、模型回退、审核授权、outbox 端到端和时间窗口测试。

当前环境未安装 pytest 时，Phase 1 测试使用标准库 `unittest discover` 可运行，同时保持 pytest 可发现形式。没有测试 MySQL 时，MySQL 集成用例明确 skip，不能声明真实并发行为已验证。

## 22. Linux 与多主机兼容边界

跨平台约束如下：

- 路径使用 `pathlib.Path`，相对路径按代码定位的仓库根解析。
- CLI 使用 `python -m backend.crawler.cli`，不依赖 shell 专属语法。
- 时间在数据库中保存 UTC 无歧义值，调度窗口通过明确时区 `Asia/Shanghai` 解释。
- worker 标识不依赖 Windows 用户名；默认由 hostname 与 PID 组成，可显式配置。
- 队列正确性只依赖 MySQL 事务、行锁、租约和稳定 UID，不依赖本地文件锁。
- 多主机共享数据库与图标对象存储时，任务协议不变；本地图标存储通过存储适配器替换。
- Scheduler 通过数据库唯一 run 和行锁选主；多实例只能有一个实例创建同一 run。
- Linux 使用 systemd timer/cron 替代 Windows 任务计划，但调用相同 controller/stop CLI。

这些边界使单机模块可以逐步拆为独立服务，而无需修改状态机、事件 UID、任务载荷版本和正式库同步契约。
