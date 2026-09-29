# 第一阶段：资源质量与推荐链路（2026-09-25）

第一阶段收尾的代码与隔离环境验证已完成。**39 条获批记录中 23 条可靠映射，16 条仍未解决；未执行正式数据迁移。** 没有推送、部署、操作生产库或清空现有数据库。工作区原有未提交修改保留，本轮未调整页面布局或动画。

## 实际入口与数据审计

项目目录为 `D:\study\智汇\wwww_git`。README、Compose 和 Vite 配置一致指向 `backend/frontend`；后端入口为 `backend/app.py` / `backend/wsgi.py`。根目录 `package.json` 不是应用启动入口。仓库及上级目录未发现适用的 AGENTS.md。

最新只读报告：[resource-quality-20260925.json](../data/resource-quality-20260925.json)。报告使用当前本地 MySQL `nav_site` 的一致性只读事务，未将旧描述报告当作当前数据。

| 项目 | 实际结果 |
| --- | --- |
| 资源 | 1,305，均为 approved |
| 空名称、URL、摘要、描述、分类、来源 | 均为 0 |
| 无效 URL / 保守规范化后的重复 URL | 0 / 0 |
| 同名产品候选 | 5 组，仅列候选 ID |
| 重复描述（归一空白和大小写） | 0 组 |
| 有标签资源 / 标签字典记录 | 1,305 / 123 |
| 重复标签关联 | 0 |
| 职业覆盖 | 93 个职业均有正式关联，最少 6 条资源；数量不代表语义已人工核验 |
| is_free、need_login、created_at、updated_at | 各 1,305 条为空，保留未知 |
| 人群、收费模式、语言、门槛的已核验信息 | 当前未维护；未自动猜测 |

报告还列出全部现有字段的空值统计、各标签及职业覆盖。它不进行联网跳转探测，不将旧域名、同域名或同名记录自动判定为同一产品。

## 本次修改

- `backend/resource_quality.py`：复用爬虫 URL 校验和域名规范化，保留路径大小写、重复斜杠、查询顺序、片段、协议和 www 差异。爬虫抓取等价性单独列为候选，不能作为自动合并依据。
- `backend/resource_migration.py`、`backend/resource_fields.py`：版本 `20260924_resource_quality_v1`，增加字段来源声明、逻辑身份关系、变更日志。用途复用 summary/description；收费模式补充 legacy is_free 无法表达的信息。人工、网页提取、AI 建议分开，AI 建议不直接发布，网页提取不能覆盖已有文案。
- `backend/questionnaire_v3.py`：保存研究/编程/自动化的细分需求，并保存学生阶段、办公角色方向；非法嵌套输入返回校验错误。V2 历史画像仍可读取，现有 V3 画像缺失细分字段时从合法原始回答只读重建，不改写用户记录。
- `backend/recommend_service.py`：文献检索信号接入；关键词按边界匹配，避免 mail 命中 ai、capital 命中 api；理由附 `match_evidence`，给出画像字段、资源字段和实际命中值。没有证据时显示探索提示，不复用资源携带的肯定式理由。
- `backend/v1_routes.py`：职业切换优先使用该职业的正式资源关联，读取完整分页候选库；网站列表和详情按需读取字段来源、逻辑身份关系。保持原 ID、收藏、API 原有字段及分页规则。
- 前端只调整数据身份和文案：收藏、历史、常用工具不再强制小写 URL 路径/查询；收费及登录要求未知时显示“未知”；推荐理由采用中性兜底。未修改页面 CSS、布局或动画。

网站权重、职业权重、`phase1-v1` 和行为融合开关均未调整。

## 当前审核身份修复（本轮收尾）

[旧冲突预览](v3-tags-20260924-preview.json)保留为历史证据；本轮通过当前库只读快照、原审核队列及路径级身份重新验证，生成[逐条映射预览](v3-tag-identity-20260925/mapping-preview.json)、[修订审核输入](v3-tag-identity-20260925/resolved-review.json)、[迁移预览](v3-tag-identity-20260925/current-db-preview.json)和[预期回滚预览](v3-tag-identity-20260925/rollback-preview.json)。逐条记录包含旧/新 ID、名称、URL、原批准标签、依据、冲突原因和处理状态。原审核队列未修改。

| 口径 | 数量 |
| --- | --- |
| 获批审核记录 | 39 |
| 可靠映射 | 23（对应 18 个当前资源） |
| 其中需要新增关联的记录 | 20 |
| 其中重复审核、无需单独迁移的记录 | 3 |
| 其中全部批准标签已经存在的记录 | 0 |
| 未解决的记录 | 16 |
| 可靠部分唯一批准关联 | 30：已有 1，待新增 29 |

23 是包含重复审核的记录数，不是资源数；20 + 3 + 16 = 39。已有的关联是 Railway 的 `DevOps`，审核代码为 `devops`。迁移现在复用推荐服务已有的标签大小写归一规则，不插入大小写重复代码；字典出现归一后歧义则拒绝迁移。初次隔离 MySQL 测试暴露了此差异，修复后重新执行全部迁移验证。因此此前“对应标签均不存在”的判断不再适用。

原因核查：当前 1,305 条资源 ID 范围为 3438–4750，source 均为 `website_seed`，原获批 ID 均已不存在。23 条在完整保守规范化 URL 和产品名上唯一一致，判定为 ID 变化；不按旧 ID、同名或域名放行，不降低路径大小写要求。当前库没有可用的别名/身份/跳转台账；已检查的旧 crawler 备份没有 websites 数据，当前导入脚本没有删除或重排 ID 的逻辑。**无法从现有证据确定造成 ID 空间变化的历史操作，原因保留未知。** 多个旧 ID 共用当前目标的情况列在 `shared_target_old_ids`，只能证明审核身份重复，不能证明历史上执行过数据库合并。

最小人工核对清单见[具体记录及原 URL](v3-tag-identity-20260925/manual-checklist.md)：

- 当前资源缺失，12 条：Insomnia 849、Postman 244、Swagger 245、MongoDB 247、PostgreSQL 248、Redis 246、Supabase 235、Sentry 386、Netlify 35、Vercel 34/520、Cypress 313。先确认是否恢复独立资源，本轮不自动新建。
- 不同产品路径，2 条：GitHub Copilot 79、Corepack 847。GitHub 或 Node.js 通用入口不能替代独立产品。
- 入口或语言变化，2 条：Node.js 92（根入口与当前 3459 的 `/docs/latest/api`）、Vue.js 84（中文入口与当前 3450 的 vuejs.org）。需要决定独立入口是否保留，不能按同品牌归并。

2026-09-25 只读联网核查：[Copilot](https://github.com/features/copilot)仍为具体产品页面；[Corepack 旧路径](https://nodejs.org/api/corepack.html)跳至 [nodejs/corepack](https://github.com/nodejs/corepack)；[Node.js 根入口](https://nodejs.org)跳至 `/en`，并非当前 API 文档入口；[Vue 中文入口](https://cn.vuejs.org)仍为中文主页。这些证据未建立与现有候选的等价身份，故均保持未解决。重复描述也未用于身份判定。

实现位于 `backend/v3_tag_identity.py`、`backend/scripts/reconcile_v3_tag_identities.py` 和 `backend/resource_migration.py`：输入绑定原审核 SHA-256、逐条源记录及完整目标身份，使用前重新计算并校验，拒绝批准范围或目标篡改。仅保留原批准子集及原依据，不自动批准候选，不修改冻结权重。新迁移版本为 `20260925_v3_tag_identity_v1`，与既有资源维护批次隔离。

复现映射、当前库只读预览及隔离验证：

```powershell
python backend/scripts/reconcile_v3_tag_identities.py --snapshot docs/recommendation/v3-tag-identity-20260925/catalog-snapshot.json
# 省略 --snapshot 可重新读取当前库；默认只读。
python backend/scripts/resource_quality.py tags-preview --input docs/recommendation/v3-tag-identity-20260925/resolved-review.json --output docs/recommendation/v3-tag-identity-20260925/current-db-preview.json
python backend/scripts/verify_v3_tag_identity_migration.py --create-isolated-test-db
```

预期回滚预览仅说明 29 个待新增关联的撤销范围，不可直接执行。隔离测试实际生成包含日志关联 ID 的可执行回滚预览。手动测试此批次时，`rollback-preview` 和 `rollback` 必须传 `--migration-version 20260925_v3_tag_identity_v1`，并保留 `--test-database` / `--preview` 约束；标签 apply 会从修订审核输入识别版本。

## AI 错误响应修复

6 个失败子用例分别为 query 缺失、null、数字、全空白、1 字符、501 字符。根因是测试仍要求旧五字段响应，而共享 `api_error` 自提交 `8c9ba2a` 已加入 `success` 和 `error_code`；收藏接口测试也明确要求这两个字段，前端通过 HTTP 状态拒绝错误并读取 msg/message。HEAD 复现只作为历史证据，不再作为忽略失败的理由。

`tests/test_ai_site_recommend_v1.py` 现在严格断言七字段完整集合与完整字典：HTTP/code 均为 400，success=false，error_code=null，legacy_code=0，data={}，message 与 msg 完全相等。保留兼容字段并加强值及类型断言，未删除、跳过或放宽断言。6 个子用例按实际输入分别验证缺失、类型、空白、长度提示。

| 子用例 | 精确错误提示 | 本轮结果 |
| --- | --- | --- |
| 缺失 query | 请输入需求描述 | 通过 |
| query=null | 需求描述必须是文本 | 通过 |
| query=123 | 需求描述必须是文本 | 通过 |
| query 全空白 | 请输入需求描述 | 通过 |
| query 为 1 字符 | 请更具体地描述你的需求 | 通过 |
| query 为 501 字符 | 需求描述不能超过 500 个字符 | 通过 |

同时修复 `backend/v1_routes.py` 的真实异常边界：可选画像连接在 try 外建立会让连接异常逃逸；现移至 try 内并安全关闭，画像不可用仍可按需求文本推荐。新增内部异常（含模拟密钥）测试，严格验证 HTTP/code=500、安全提示“推荐服务暂时不可用”、相同错误结构，响应不含内部异常或密钥。没有用成功响应掩盖失败。

`backend/scripts/verify_ai_response_contract.py` 产生真实 Flask 路由响应夹具；`backend/frontend/scripts/verify-ai-error-contract.mjs` 回放实际组件 submitRecommendation、实际 unwrapResponse 及 Axios 状态判定，覆盖 6 种 400、500、正常匹配、空结果、401 和 422 共 11 种状态。验证错误/登录/成功/空状态、提示、结果及 loading。此为函数级前端回放，不冒充浏览器端到端测试。

## 迁移、预览和回滚

在仓库根目录复现只读审计（只读取 backend/.env 配置，不导入应用启动器）：

```powershell
python backend/scripts/resource_quality.py audit --output docs/data/resource-quality-current.json
python backend/scripts/resource_quality.py tags-preview --output docs/recommendation/v3-tags-current-preview.json
python backend/scripts/resource_quality.py rollback-preview --output docs/recommendation/resource-rollback-current-preview.json
```

命令 `tags-apply`、`maintenance-apply`、`rollback` **只允许显式测试数据库**，不支持写入当前应用库或生产库。MySQL 地址必须为本机，测试库名称必须以 `_test` 结尾；使用环境变量 `RESOURCE_TEST_DATABASE_URL` 传递测试库 DSN，不把密码写入命令或提交到仓库。

以下命令需先在测试库准备资源及审核输入，并由操作者在本地配置上述环境变量：

```powershell
python backend/scripts/resource_quality.py tags-preview --test-database --input reviewed-test-queue.json --output tag-preview.json
python backend/scripts/resource_quality.py tags-apply --test-database --input reviewed-test-queue.json --preview tag-preview.json --output tag-applied.json
# 同一输入重复执行 tags-apply 不新增关联。
python backend/scripts/resource_quality.py rollback-preview --test-database --output rollback-preview.json
python backend/scripts/resource_quality.py rollback --test-database --preview rollback-preview.json --output rollback-result.json
```

字段和逻辑合并使用 `maintenance-preview` / `maintenance-apply`，输入为 JSON 数组：

```json
[
  {"kind":"field","site_id":1,"url":"https://example.test/API","field":"audience","value":null,"source_kind":"manual","source_ref":"test-fixture","verified_at":null},
  {"kind":"merge","source_id":1,"target_id":2,"source_url":"https://example.test/API","target_url":"https://example.test/Other","reviewed":true,"evidence":"仅为测试结构示例，不能作为真实合并依据"}
]
```

先预览，再使用相同输入与 `--preview` 执行。工具复核资源身份及预览内容，拒绝循环/链式合并，MySQL 变更使用命名锁和事务。逻辑合并保留两条资源及其全部收藏、标签、历史引用，仅新增可回滚的来源→目标关系；API 以 `canonical_site_id` 和 `identity_evidence` 暴露关系，**不会删除资源、重排分页或自动搬迁用户关联**。

加表 SQL 位于 `backend/sql/migrations/20260924_resource_quality.up.sql`。MySQL DDL 隐式提交，因此加表和数据事务分开；回滚通过变更日志精确撤销本批次创建的 site_tags 关联，并将来源声明/身份关系标记为 reverted。保留字典、日志及全部业务资源，不使用 DROP TABLE。当前库的[回滚预览](resource-quality-rollback-20260925-preview.json)为空，因为本阶段没有向当前库写入变更。

本阶段仅测试库运行了迁移，应用运行无需先给当前库加表；代码兼容缺少新表。未来明确授权应用数据迁移后，应先完成身份复核与备份，并在重启后验收字段投影。

## 实际验证

- `python backend/scripts/verify_resource_chain.py --create-isolated-test-db --output docs/data/resource-chain-20260925-test.json`：真实 Flask 路由 + 独立 MySQL，40 项检查。包括问卷保存、文献/接口两种需求、职业切换实际资源 ID 变化、理由证据、V2 读取、空画像、少候选、收藏幂等、分页不同页、字段来源、逻辑合并保留引用、迁移 CLI 强制预览、重复执行及回滚。[完整结果](../data/resource-chain-20260925-test.json)
- `python -m unittest discover -s tests -p test_resource_quality_stage1.py`：8 项，包含 URL 边界、审核 ID 漂移、未批准标签、重复执行、回滚保护、人工来源优先、嵌套输入和两种需求。
- 本轮 `python backend/scripts/verify_stage1_regressions.py` 全部通过，共 151 项：资源质量 8、身份映射 10、问卷 V1/V2/V3 23、职业 9、网站个性化 4、审核队列 3、排序接口 3、收藏 27、登录鉴权 33、AI 推荐 20、普通搜索 11。AI 的 6 个输入子用例计在同一测试方法内。[逐组结果](../data/stage1-regression-results.json)
- `python backend/scripts/verify_v3_tag_identity_migration.py --create-isolated-test-db`：独立 MySQL 12 项检查通过。复制公开资源目录而非用户数据，额外构造一个前批次已有标签；在原本待增 29 个关联中提前存在 1 个，因此本批实际新增 28 个。检查重复执行零新增、原关联保留、前批版本不受影响、回滚精确恢复原集合、字典不删、重复回滚无操作。[完整结果](../data/stage1-tag-identity-mysql-test.json)
- `python backend/scripts/verify_ai_response_contract.py` 和 `node backend/frontend/scripts/verify-ai-error-contract.mjs`：实际后端响应与前端函数回放共 11 种状态全部通过。[响应夹具](../data/stage1-ai-response-contract.json)
- 前端职业切换 59 项检查，以及推荐理由、收藏交互、收藏状态统一、登录状态、常用工具轮换、浏览历史和新增 URL 身份检查通过。新增命令：`node backend/frontend/scripts/verify-resource-identity.mjs`。
- `npm run build`（工作目录 backend/frontend）成功。沙箱内首次构建因 Vite 子进程 spawn EPERM 失败，允许的本地沙箱外构建成功；未部署产物。
- Python 修改文件通过 compileall 语法检查。

隔离测试不复制真实用户、密码、收藏或行为。本轮链路测试库为 `resource_chain_512bcc0dde82_test`，标签迁移测试库为 `v3_tag_identity_e7723631b2c4_test`，CLI 预览、执行及回滚结果保留在同名 `artifacts/` 子目录。首次暴露 DevOps 差异的测试库与中间调试库均保留，没有清空或删除。

前端三个既有检查曾因新增 class、当前按钮结构和 CRLF 换行不匹配而失败；已修复定位方式，保留收藏按钮不嵌套链接、访问事件分发和状态统一的行为约束。理由测试另增加“不得肯定式兜底”的断言。

## 遗留问题与验证边界

1. 真实批准标签未落库（遵守本次范围）：23 条可靠映射已有可审阅预览，16 条仍需人工判断，未纳入迁移。
2. 未核实价格、人群、语言、门槛、真实别名或跳转关系；相应字段继续未知，没有联网臆测补全。
3. AI 推荐 6 个既有失败子用例已按当前契约修复并通过，额外异常与前端响应回放通过。[旧基线核对](../data/stage1-ai-baseline-check.json)仅为历史记录，不代表当前测试状态。正常 AI 测试使用隔离服务夹具，未验证外部模型供应商可用性。
4. 本阶段是隔离 MySQL 的接口级业务验收和前端脚本/构建验收，未使用真实用户完成浏览器端全流程，也未验收线上 Redis/Meilisearch 集群。

本地启动沿用既有方式：根目录 `python backend/app.py`，另一个终端 `npm run dev --prefix backend/frontend`；本阶段没有自动启动或部署正式服务。

**第二阶段条件：本轮允许执行的代码、预览与隔离验证已完成，但尚不具备完整资源数据验收条件。** 16 条身份需人工确认，正式迁移未执行；可靠子集已具备后续审阅条件。未进入第二阶段。
