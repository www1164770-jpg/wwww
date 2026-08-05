# 网站爬虫系统分阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以五个可独立验收的阶段，从安全任务基础设施演进为 Windows 夜间运行、可审核并可幂等同步的网站发现系统。

**Architecture:** 所有阶段围绕独立 `zhihui_crawler` MySQL、持久任务/租约、稳定 UID 和 Outbox 协议演进。抓取、分析、审核和同步模块以数据库任务解耦，现有 Flask 应用与正式数据库不会成为爬虫运行时依赖。

**Tech Stack:** Python 3.13、SQLAlchemy 2.x、MySQL/PyMySQL、unittest/pytest 兼容测试；后续阶段使用 Scrapy、Playwright、Ollama 和现有 Vue/Flask 管理端。

## Global Constraints

- 只访问公开资源，遵守 robots.txt，不绕过登录、验证码、Cloudflare、付费墙或访问控制。
- 排除成人、赌博、毒品、武器、诈骗、钓鱼、恶意软件、盗版下载和仇恨极端内容。
- 爬虫数据只写 `CRAWLER_DATABASE_URL` 指向的独立数据库；正式库名为 `zhihui_crawler`，测试库名必须包含 `test`。
- Windows 夜间窗口为 01:00–05:00；05:00 后停止新租赁，已租赁任务可结束。
- 默认每晚目标 3,000 个网站，首期候选规模约 100,000。
- 不记录 Authorization、Cookie、数据库密码、完整正文或个人敏感信息。
- 路径使用 `pathlib.Path`，命令不依赖当前工作目录。
- 每个阶段先写失败测试，再做最小实现，再运行相关回归。
- 不执行 Git 暂存、提交、推送、重置、checkout 或 clean。

---

## Phase 1：基础设施

### 输入条件

- 仓库现有 Flask、SQLAlchemy、PyMySQL 和自定义迁移模式已确认。
- 已批准设计文档 `docs/superpowers/specs/2026-07-30-web-crawler-system-design.md`。
- 独立 MySQL URL 可由操作员在冒烟测试时显式提供；没有 URL 不阻塞普通应用。

### 输出成果

- `backend/crawler/` 独立包与配置。
- 五张基础表、MySQL 迁移和迁移库名安全门。
- 任务入队、租赁、完成、失败、取消、重试和租约恢复。
- worker 心跳、crawl run、outbox 原语。
- 九个安全 CLI 命令与 JSON 结构化日志。
- SQLite 单元/事务测试、MySQL SQL 编译测试和可选 MySQL 集成测试。

### 文件范围

- 新增：`backend/crawler/**`
- 新增：`tests/crawler/**`
- 新增：`backend/data/crawler/README.md`
- 新增：`backend/crawler/.env.example`
- 修改：`.gitignore`
- 不修改：现有前端、Flask 路由、职业推荐、SiteCard、收藏逻辑、正式库模型和现有迁移。

### 测试要求

- `python -m unittest discover -s tests/crawler -p "test_*.py" -v`
- `python -m compileall -q backend tests`
- MySQL 查询必须编译出 `FOR UPDATE SKIP LOCKED`。
- 显式测试库可用时运行 MySQL 集成用例，否则报告 skip。
- 执行现有职业/推荐定向测试和前端构建脚本。

### 验收标准

- 缺少 `CRAWLER_DATABASE_URL` 时普通 Flask 应用仍可导入，爬虫 CLI 清晰非零退出。
- 活跃任务并发防重，终态后允许新代任务。
- 两个 worker 不能同时租赁同一行；过期租约幂等恢复。
- stop_requested 阻止该 run 新租赁，已租赁任务可完成。
- outbox event UID 幂等，processed 不再租赁。
- CLI JSON 有效且数据库错误不伪装成空结果。
- 迁移拒绝正式项目库名，不自动创建数据库、不删除数据。

### 本阶段不实现

Scrapy、Playwright、RSS/Atom/Sitemap、Common Crawl、完整 URL 归并、正文快照、Ollama、风险模型、图标下载、管理员页面、正式库同步、Windows 任务注册或真实全网抓取。

### 下一阶段接口

Phase 2 只依赖 `enqueue_task()`、`lease_tasks()`、任务完成/失败 API、run 状态、结构化日志和版本化 JSON payload。Discovery 使用 `task_type="fetch_url"`，Fetch 写新快照表并产生 `analysis` 任务；Phase 1 表不需要破坏性改名。

## Phase 2：静态抓取 MVP

### 输入条件

- Phase 1 队列、租约恢复、run 和 CLI 在 MySQL 测试库通过。
- 合规与 SSRF 策略已有可执行规则清单。

### 输出成果

- 免费 discovery Provider 接口及 RSS、Atom、Sitemap 实现。
- Scrapy 静态抓取 worker。
- robots.txt、域名并发 1、1–3 秒间隔、全局并发 24。
- 首页加最多 5 个关键页限制。
- 完整 URL/域名规范化、快照和候选站点生命周期。

### 文件范围

- 新增：`backend/crawler/discovery/**`
- 新增：`backend/crawler/fetch/**`
- 新增：`backend/crawler/db/models_discovery.py`、`models_fetch.py`
- 新增：对应向前迁移和 `tests/crawler/discovery/**`、`tests/crawler/fetch/**`
- 修改：依赖文件，只添加本阶段实际使用的 Scrapy/解析依赖。

### 测试要求

- 本地 HTTP 夹具覆盖 robots、重定向、大小/MIME、超时和页面上限。
- URL 规范化表驱动测试。
- SSRF 测试覆盖环回、私网、链路本地、元数据地址与 DNS 重绑定。
- 抓取重试与不可重试错误分类测试。

### 验收标准

- 不访问 robots 禁止路径，不超出每站页面上限。
- 不抓私网或受控资源。
- 相同发现 URL 幂等，相同内容哈希避免重复分析。
- 静态抓取失败能安全重试或进入明确终态。

### 本阶段不实现

Playwright、Ollama、中文生成、最终风险模型、人工审核 UI、正式库同步、Windows 自动注册。

### 下一阶段接口

输出不可变 `fetch_snapshot_uid`、候选站点 UID、内容对象引用、语言线索和 `analysis` 任务 payload；Phase 3 不直接重新抓网页。

## Phase 3：分析、安全与资源

### 输入条件

- Phase 2 能稳定产生受控快照和候选站点。
- 风险类别、硬拒绝规则和自动批准阈值已版本化。

### 输出成果

- 规则提取、语言检测、分类与质量评分。
- 低置信度 Ollama 降级、中文摘要与标签。
- 硬风险过滤、风险评分和可解释证据。
- favicon/logo 安全下载、内容寻址缓存。

### 文件范围

- 新增：`backend/crawler/analysis/**`
- 新增：`backend/crawler/risk/**`
- 新增：`backend/crawler/assets/**`
- 新增：分析/风险/图标模型和向前迁移。
- 修改：依赖文件，只添加已选定的语言、模型客户端和图像验证依赖。

### 测试要求

- 规则优先与 Ollama 不调用路径。
- Ollama 超时、无效 JSON、显存不足的回退。
- 多语言样本、中文摘要长度和来源事实一致性。
- 禁止类别、模型不能覆盖硬拒绝、图像炸弹/伪 MIME 防护。

### 验收标准

- 高置信规则结果不调用模型。
- 模型不可用不丢任务且不伪造成功。
- 高风险候选自动拒绝，中风险标为 review_required。
- 图标只写配置目录，数据库保存相对路径和哈希。

### 本阶段不实现

管理 UI、正式库同步、Playwright、Windows 夜间自动运行。

### 下一阶段接口

输出版本化分析结果、风险结论与 review 状态；批准事务可与 `enqueue_outbox_event()` 使用同一 crawler session。

## Phase 4：审核与正式库同步

### 输入条件

- Phase 3 风险决策可解释且有稳定候选 UID。
- 正式系统字段白名单、幂等键与管理员权限规则已批准。

### 输出成果

- 仅管理员可访问的 crawler API 与管理前端。
- 人工批准/拒绝/重跑、审计记录。
- 审核批准事务内写 outbox。
- Outbox Worker 对正式系统的幂等同步和回执。

### 文件范围

- 新增：`backend/crawler/review/**`、`backend/crawler/sync/**`
- 新增或隔离注册：crawler 管理 API blueprint。
- 新增：管理前端页面与 API client。
- 新增：审核、审计、同步回执模型和迁移。
- 修改：现有鉴权接入点，仅复用管理员身份与角色，不修改普通用户流程。

### 测试要求

- 非管理员 401/403、管理员最小权限。
- 并发审核、重复提交、审计不可缺失。
- outbox 与批准同事务。
- 正式端超时/冲突/重复 event UID 的幂等同步。
- 字段白名单与敏感证据不出 crawler 边界。

### 验收标准

- 只有管理员可审核。
- 每次状态变更均有 actor、前后状态和原因。
- 批准后最终可同步，重复消费不产生重复正式站点。
- crawler DB 或正式端失败不会造成静默丢事件。

### 本阶段不实现

Playwright 动态降级、Windows 自动调度、完整运维监控。

### 下一阶段接口

Phase 5 复用现有 worker/queue/outbox CLI，新增 controller 与资源控制；不更改审核或同步事件协议。

## Phase 5：动态抓取与夜间运行

### 输入条件

- Phase 1–4 在测试环境端到端通过。
- 已确定 Windows 运行账户、Python 环境、GPU/内存预算和日志目录权限。

### 输出成果

- 静态正文无效时的 Playwright 按需降级。
- 浏览器并发 2、超时、内存和进程回收。
- Windows Task Scheduler 注册/卸载脚本。
- 01:00 controller 与 05:00 stop 请求。
- 运行指标、告警、保留清理和运维手册。

### 文件范围

- 新增：`backend/crawler/fetch/browser/**`
- 新增：`backend/crawler/controller/**`
- 新增：`backend/crawler/platform/windows/**`
- 新增：`backend/crawler/maintenance/**`
- 新增：动态抓取、调度窗口和故障注入测试。
- 修改：依赖文件，加入锁定的 Playwright 版本及浏览器安装说明。

### 测试要求

- 静态有效时绝不启动浏览器。
- 浏览器超时、崩溃、孤儿进程和资源上限测试。
- 01:00/05:00 时钟边界与跨日测试。
- stop_requested 不租新任务、已租任务可完成。
- Windows 脚本 dry-run、安装/卸载幂等和路径含空格测试。
- 清理任务只处理超过保留期的终态数据。

### 验收标准

- 每晚 controller 可恢复启动且只有一个活跃 run。
- 05:00 后无新租赁，进程在宽限期内退出。
- 动态抓取受资源预算约束，不成为默认路径。
- 运维人员可从 status、日志和指标定位积压、stale worker 和死信。
- Windows 任务可安全安装、检查和卸载。

### 本阶段不实现

付费搜索 Provider、访问控制绕过、无限递归、自动横向扩容。

### 后续多主机接口

Linux 使用 systemd timer 调用同一 CLI；多主机共享 MySQL 并依赖 `SKIP LOCKED` 和租约。图标存储可替换为对象存储适配器，Scheduler 使用 run UID 与数据库锁选主，任务和 outbox payload 保持版本兼容。
