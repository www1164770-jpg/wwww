# 第二阶段：统一搜索与索引同步

2026-09-25。本阶段已修改代码并完成本地隔离验证；未推送、部署、修改正式库或进入第三阶段。已有未提交修改保留，未修改页面布局、CSS 或动画。

第一阶段的 16 条身份未决记录继续隔离，原审核队列未修改。再次对当前库只读核验：[批准标签预览](stage1-tags-still-pending.json)仍为 **29 个待新增关联、1 个已有关联**，没有把待审映射、AI 建议或未核实字段写入搜索数据。

## 实际入口与调用路径

实际入口为 `backend/app.py` / `backend/wsgi.py` 和 `backend/frontend`，根目录不是正式前端。仓库及上级没有适用 AGENTS.md。当前本地配置使用 MySQL `nav_site`；只读检查有 1,305 条 approved 公共资源，搜索迁移尚未安装（revision/indexed_revision 均为空），未自动启用正式同步工作进程。

| 入口 | 实际调用及本次行为 |
| --- | --- |
| 首页 HeroSearch / SearchBar 站内搜索 | 跳转 `/search?q=...` → Pinia search store → `GET /api/sites/search`；`/api/search` 兼容别名保留 |
| 外部搜索引擎 | SearchBar 按原规则打开外部搜索，未改为站内检索 |
| 探索/搜索结果页 | 当前 router 使用 SearchResults；旧独立 Categories/CategoryDetail 页面已不在现有工作区，未恢复或重做。分类、页码和排序继续写在 URL 中 |
| 列表接口带关键词 | `GET /api/sites?q=...` / keyword 共用候选服务，保留原分类含子分类、标签、免费/地区过滤、排序及分页 SQL |
| 无关键词的首页热门/推荐列表 | 沿用既有数据库列表和推荐逻辑；增加公共状态/启用校验，不改推荐权重 |
| 搜索建议 | `/api/sites/search/suggest`、`/api/search/suggest` 共用候选检索，保留分类建议及最多 8 项的结构 |
| AI 找网站 | 登录后 `POST /api/ai/site-recommend`，复用 `extract_query_terms` 的原意图词进入公共候选服务，再用原 `recommend_sites_for_query` 评分与理由；未开展第三阶段 |
| 私有收藏 | 保持原鉴权及收藏接口；没有加入公共索引或公共 Redis 候选缓存 |

实际 app 入口显式注入统一 SearchService。未传服务的旧测试/嵌入式 `register_v1_routes` 调用保留兼容的数据库适配路径；正常 app 不使用该进程内搜索缓存。

## 修改文件

- `backend/search_service.py`：Meilisearch HTTP/异步任务适配、公共文档、共享候选、Redis 候选缓存、明确的故障分类和检索日志。
- `backend/search_catalog.py`：一致性只读快照、当前资源/标签/职业/分类投影及数据库版本；不读取用户或收藏。
- `backend/search_migration.py`：版本 `20260925_search_sync_v1`，事务触发器、预览、幂等加表及回滚预览；拒绝非 InnoDB 业务表。
- `backend/search_sync.py`：复用 outbox 租约/失败处理，确认索引任务结果、持久化任务恢复、对账、安全重建和人工重试。
- `backend/crawler/outbox/service.py`：租约查询新增可选 event_type 过滤，原调用接口兼容；搜索消费者不会领取其他爬虫事件。
- `backend/v1_routes.py`、`backend/app.py`：接入共享检索；审核发布不再提交后直接推索引并谎报同步成功；公共状态及错误响应保持明确。
- `backend/frontend/src/stores/search.js`、`src/utils/api.js`：复用缓存前请求 `/api/search/version`；版本变化或同步未完成时刷新；无法验证当前状态时不展示旧公共结果。
- `backend/scripts/search_sync.py`：只读运维和显式隔离测试命令；`verify_search_sync.py`：可复现的真实服务联调。
- `compose.yaml`、两份 `.env.example`：搜索工作进程及显式启用配置。
- `backend/frontend/scripts/verify-search-version-cache.mjs`：回放真实 Pinia store 代码验证版本和下架行为，未放宽既有测试断言。

## 搜索文档、过滤与故障处理

文档复用 name、aliases（存在时）、summary、description、tags、occupations、use_cases（存在时）、category_id/name、公共状态、已有排序字段和文档指纹。不存在或未核实的字段保持空值，不补充价格、用途事实或品牌别名。URL 去重仅规范化协议和域名大小写，保留路径和查询大小写；不按域名合并产品。

可搜索字段按名称、别名、标签、摘要、描述、用途、职业、分类、URL 配置；分类/标签/职业/状态/启用可筛选；点击量、推荐级别、质量分、更新时间和 ID 可排序。Meilisearch 排名把 exactness 放在 sort 之前。普通 API 保留原 relevance/name/latest/recommend 排序及 `matchedFields`，relevance 明确名称优先，不让热门 Vue Theme 超过 Vue；显式 recommend 则保留原推荐排序语义。

检索获取所有匹配分页后，使用当前数据库资源信息生成卡片并分页，过滤下架、禁用、已删除、未审核项，避免旧索引候选占满一页却返回不足。当前实现每次获取公开目录快照，适合现有目录规模；不是大规模检索性能优化。索引 maxTotalHits 为 100,000，目录达到这一规模会明确拒绝同步，不能静默截断。

网络断开、连接/读取超时、Meilisearch 5xx/429 才产生 `database` 故障降级。正常零结果仍是成功的 Meilisearch 空结果；多词/别名的词项放宽属于检索规则，不是数据库故障降级。401/403、索引不存在、无效筛选/排序等 4xx 和失败异步任务为明确错误，不静默改查数据库。SQL 错误继续上抛，客户端得到安全错误结构。

原响应结构保留；普通搜索新增兼容 `retrieval` 元信息，含 source、durationMs、fallbackReason、cached、dataVersion。AI 保留原响应结构，通过检索日志记录来源及耗时。日志不记录原始需求、密钥或上游响应正文。

## 事务同步与缓存顺序

1. 正式资源的 INSERT/UPDATE/DELETE 触发器在同一 InnoDB 事务内递增 `search_sync_state.revision` 并写入已有 `OutboxEvent` 模型的 `outbox_events`。事务回滚同时撤销数据、版本和事件。此表与业务表同库，以满足原子提交；未增加 Redis 队列或另一套队列机制。
2. 覆盖 websites、site_tags、tags、site_occupations、categories；因此后台新增/编辑/审核/下架/软删除、旧 ORM 硬删除、分类编辑、标签改名及关联、职业关联、导入和描述修正均被捕获。已有 resource_field_claims、resource_identity_links 表存在时也覆盖来源维护与逻辑合并；当前库尚无这两张表，未来安装第一阶段字段迁移后必须重新预览安装对应触发器。
3. 入口核查包括 `v1_routes` 的后台 CRUD、sync_site_tags、site_occupations 写入，`app.py` 的审核/旧 REST CRUD/导入，`import_category_sites.py`、description 修正脚本、`resource_migration.py`，以及 click/favorite 排序计数更新。无需在每个 SQL/ORM 调用后另发事件。DDL/TRUNCATE 不属于正常资源写入口，不允许用其替代业务删除。
4. 工作进程用现有 lease/fail/processed 原语领取 search.changed，每批最多 100 个；MySQL 命名锁串行化 worker、重试和重建。事件仅唤醒同步，**不使用事件内旧文档**。每批读取当前一致性快照，将最新公共目录合并写入索引并删除多余文档。当前采用批次全目录投影，未实现细粒度按 ID 增量性能优化。
5. Meilisearch 返回 taskUid 后仍轮询最终 succeeded；失败/取消不推进 indexed_revision。任务 ID 保存在 MySQL，超时或进程重启先确认旧任务，再提交新任务。提交前写入 -1 哨兵；若 HTTP 超时导致是否入队未知，阻止后续写入，须人工 recover，不能盲目重复 swap。
6. 工作进程崩溃后回收过期租约；指数退避沿用 crawler 原语，触发器事件最多 5 次。超过次数保留 dead、last_error 与事件 UID；retry 显式恢复。命名锁仍被持有期间其他工作进程不会因租约时间到而并发提交。
7. 只有最终索引任务成功才推进 indexed_revision 并完成本批事件。数据库业务保存成功仍返回成功，“索引待同步”单独说明；不会因为索引失败把已提交业务伪装成保存失败。

Redis 键包含数据库主机/端口/库名、索引主机/名称、查询/扩展词、分类、排序、页码、页大小、AI 模式及 DB/index 两个版本。数据一提交就变成新 revision，旧键无法再命中；两版本不一致时不读写索引候选缓存，并用当前数据库匹配作明确的 `meilisearch+pending_database` 一致性补充，确保新标签可查、旧内容不重新缓存。索引成功后才使用新的同版本缓存键。Redis 故障跳过缓存，搜索继续。

即使命中 Redis，也重新读取当前公共状态；前端五分钟缓存同样先校验服务器版本，未安装迁移或仍有同步差异时禁止直接复用。旧缓存过期即可回收，无需全局 FLUSHDB。

## 配置、启动和停止

| 配置 | 说明 |
| --- | --- |
| SEARCH_BACKEND | 默认 meilisearch；database 为显式运维回退，不伪装为主检索 |
| MEILI_HOST / MEILI_MASTER_KEY / MEILI_INDEX | 搜索地址、服务端密钥、索引名；默认本机 7700 / websites |
| REDIS_URL | 沿用现有 Redis 地址；未配置或不可用允许无缓存运行 |
| MYSQL_* / DB_* | 沿用 db_pool 优先级，不使用 crawler 独立数据库配置冒充业务库 |
| SEARCH_SYNC_ENABLED | 独立 worker 的显式启用开关；原生默认 0 |
| COMPOSE_PROFILES=search-sync | 启用 Compose search-worker；默认不启用，避免未审阅迁移时写正式数据 |
| SEARCH_TEST_DATABASE_URL / SEARCH_TEST_INDEX | 运维变更测试目标；强制 localhost、`*_test` 库、`stage2_test_*` 索引 |

原启动方式不变：`python backend/app.py`，另一个终端 `npm run dev --prefix backend/frontend`。`start.bat` 使用 compose up、stop.bat 使用 compose down、status.bat 使用 compose ps，均兼容增加的 profile，且不会删除卷。本轮未运行这些脚本去启动正式服务。

后续审阅迁移并明确授权启用后，可设置 `COMPOSE_PROFILES=search-sync` 再运行 start.bat，或 `docker compose --profile search-sync up -d search-worker`；停止 worker：`docker compose --profile search-sync stop search-worker`；查看状态：`docker compose --profile search-sync ps`。原生 worker：设置 `SEARCH_SYNC_ENABLED=1` 后运行 `python backend/scripts/search_sync.py worker`，Ctrl+C 停止。这里是后续操作说明，本轮未启用正式 worker。

## 迁移、对账、重建、重试与回退

[当前库迁移预览](stage2-current-migration-preview.json)包含版本、目标库、加表及触发器语句、回滚语句。MySQL DDL 隐式提交，因此应在维护窗口先审阅安装捕获、再重建；不能声称触发器安装过程整体可事务回滚。失败后可重复预览安装缺失部分。没有自动执行正式 DDL。

测试库 DSN 由操作者在本地环境设置，不写密码到文件/命令历史。以下为仓库根目录命令，必须配置独立测试库和索引：

```powershell
python backend/scripts/search_sync.py migration-preview --test-database --output migration-preview.json
python backend/scripts/search_sync.py migration-apply --test-database --preview migration-preview.json --output migration-result.json
# 仅在测试索引不存在时创建；已有索引不会被清空或删除。
python backend/scripts/search_sync.py initialize-index --test-database
python backend/scripts/search_sync.py rebuild --test-database --output rebuild-result.json
python backend/scripts/search_sync.py once --test-database
python backend/scripts/search_sync.py status --test-database
python backend/scripts/search_sync.py reconcile --test-database --output reconciliation.json
python backend/scripts/search_sync.py retry --test-database
python backend/scripts/search_sync.py once --test-database
```

reconcile 比较当前公共文档与索引，分别报告 missing、stale、not_public_or_removed。不会修改索引。省略 `--test-database` 的 migration-preview / status / reconcile 为当前库只读操作；维护写命令拒绝正式库。

rebuild 先建独立临时索引，等待设置及文档任务成功，再重读目录纳入构建期间的新增/修改/删除，逐项校验设置与文档，最后等待原子 swap 成功。旧索引保留在返回的 retained_previous_index 名下，没有先清空在线索引。校验时版本变化则中止切换，留下临时索引供检查；可重新执行 rebuild。切换边界提交的数据保留其 outbox 事件，DB/index 版本不同让查询先用当前状态，随后 worker 追平。重建不会批量标记并发事件完成。

若 task_id=-1：先停止同步进程，核查该 Meilisearch 实例未完成/正在提交的任务及网络状态，再显式 `recover --test-database`。recover 等待引擎已入队任务终结并解除哨兵，不认为已同步成功；随后 retry、once 或 fresh rebuild。不要自动重放一个结果未知的 swap。该极端状态有意要求人工恢复，以免迟到任务逆转索引。

回退首选 `SEARCH_BACKEND=database` 并重启应用，停止 worker，保留 outbox 等待修复；无需回滚业务数据。旧索引不宜直接 swap 回去（可能包含后来已下架内容），应重新对账、重建当前数据库投影。迁移回滚只删除本版本捕获触发器，保留资源、关联、索引、版本与事件历史：

```powershell
python backend/scripts/search_sync.py migration-rollback-preview --test-database --output rollback-preview.json
python backend/scripts/search_sync.py migration-rollback --test-database --preview rollback-preview.json --output rollback-result.json
```

## 实际验证与边界

- [真实服务联调结果](stage2-verification.json)：**85 项通过**。本地 Python 3.14.5、MySQL 9.7.1；独立 Docker Meilisearch 1.12.8（17700）、Redis 7.4.11（16379），无现有业务卷。初始固定 8 个合成资源，6 个可公开，另含禁用和待审核各 1 个；重建期间新增第 9 个。使用新建 `search_sync_5308b5298119_test` 和唯一 stage2_test 索引，不复制真实用户。另起 Python 进程验证 Redis 缓存共享；补验迁移回滚使缓存版本失效，再经 CLI 重建恢复。
- 联调覆盖名称/别名/标签/职业/用途、分类、准确页码和排序顺序、修改标签即时检索与索引生效、下架/删除即时隐藏及索引清理、重复/迟到旧事件、并发 worker 串行化、事务回滚、死信及人工重试、租约过期、新进程恢复已提交 taskUid、实际失败索引任务、提交状态未知的恢复门禁、Meilisearch 故障/正常零结果/配置错误、Redis 故障、重建期间及 swap 边界的变更、对账三类差异、迁移重复执行/CLI 预览校验及回滚保留数据。
- [既有回归](stage2-regression-results.json)：151 项通过，包含 AI 20（原 6 个失败子用例均严格验证）、搜索 11、收藏 27、鉴权 33、职业 9、问卷 23，以及第一阶段身份/资源/推荐测试。另有 crawler outbox 原测试 6 项通过。
- [隔离 MySQL 业务链路](stage2-resource-chain.json)：40 项通过，问卷→画像→推荐理由、职业切换、收藏/分页及资源维护回滚未回归。
- 前端搜索静态检查 47 项、职业切换 59 项、AI 11 种实际响应回放通过；新增真实 store 函数回放覆盖缓存命中、版本改变、同步中绕过缓存、下架和版本检查不可用。没有削弱旧断言。
- `npm run build` 成功；`docker compose --profile search-sync config --quiet` 成功；Python compileall 成功。构建需要已确认的本地沙箱外子进程权限，未部署产物。

固定查询每种分别执行一次冷 Redis 键和一次暖键（引擎已完成构建，**不是冷磁盘/冷进程**）。以下为候选服务耗时，包含数据库当前状态读取；不包含浏览器网络/UI，不是生产性能或统计分位数。6 个查询的首位结果均符合固定预期，冷暖各验证一次：

| 查询 | 预期首位 ID | 冷键 ms | 暖键 ms |
| --- | --- | --- | --- |
| Paper Atlas | 1 | 7.185 | 3.903 |
| 文献检索 | 1 | 5.863 | 3.905 |
| literature | 1 | 5.441 | 3.051 |
| 接口调试 | 2 | 5.855 | 3.128 |
| 科研人员 | 1 | 4.964 | 3.120 |
| Vue | 3 | 5.038 | 4.180 |

复现：`python backend/scripts/verify_search_sync.py --create-isolated-test-db`，需本机独立测试 Meilisearch 17700、Redis 16379；报告会更新至新测试库和新实测值。CLI 迁移、回滚、状态和对账文件位于同名 `artifacts/search_sync_5308b5298119_test/`。中间调试库/索引未清空或删除。调试中暴露并修复了索引设置无序字段比较、秒级 outbox 时间舍入和跨测试库缓存命名空间问题，最终结果为重新运行后的通过结果。

未验证：正式库触发器部署、完整 Compose MySQL 8.4 组合运行、生产权限/复制拓扑、长时间大并发压测、实际浏览器全流程及外部 AI 供应商。本轮验证的是单机独立服务和固定数据，不声称这些线上场景已通过。当前全目录投影及查询状态校验有明确规模成本，后续如需优化须保持上述一致性语义。

第二阶段开发与本地验收完成，停止扩大测试范围；正式启用仍须审阅迁移和环境配置。第一阶段未决身份及待新增标签保持原状态，未进入第三阶段。

测试结束后已停止本次创建的 `zhihangyu-stage2-meili-test`、`zhihangyu-stage2-redis-test` 容器，未删除容器、索引或数据库；需要复查时可用 `docker start zhihangyu-stage2-meili-test zhihangyu-stage2-redis-test` 恢复独立测试服务。
