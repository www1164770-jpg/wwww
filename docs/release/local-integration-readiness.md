# 前五阶段本地集成验收与启用准备

## 9月29日最终专项验收与日常启用方案（本节优先）

本次只完成亚秒曝光、相似页及其具体缺陷回归，没有重跑已通过的整套测试。没有推送、部署、修改日常数据库或启用日常新策略。以下历史段落中“相似页/亚秒曝光待补验”已由本节更新；历史记录保留供追溯。

### 两项专项结果

**曝光边界通过，区分三层证据：**

- 代码口径仍为可见比例≥0.5、连续1000ms；隐藏、离屏或卸载取消计时，回前台重新计满1000ms，不累计后台时间。没有修改曝光产品代码。
- `artifacts/local-integration/visibility-clock.json`：执行真实 `visibilityWindow` 和 `recommendationVisibility` 模块，注入模拟时钟、DOM、账号和传输。10项断言覆盖49.9%、50%、999/1000ms、后台10000ms、10次快速切换、旧账号计时器、新账号独立去重、返回旧账号去重和卸载取消。它是确定性模拟测试，不冒充原生浏览器切换。
- `visibility-browser-clock.json`：真实Chromium、真实模块和隔离HTTP，模拟时钟/visibility/IntersectionObserver。成功批次 `special-clock-1790643657650` 为账号2和1各一条。`special-final-audit.json` 从隔离MySQL只读确认归属，无重复。首次探针在Axios微任务发送前断言失败，已校正为等待微任务；不是曝光业务失败，也没有拿失败探针混充成功证据。
- `visibility-native.json`：真实Chromium标签切换、原生IntersectionObserver、原生visibilitychange和实际墙钟，未覆盖可见性属性或时钟。最终在已实际显示的相似卡片上挂载现有曝光观察函数：3.2ms确认比例1，38ms进入hidden（约34.8ms后、远早于1000ms），1612.8ms回visible（后台1574.8ms），2626.6ms发送唯一请求（回前台1013.8ms），2657.8ms收到HTTP 200。批次 `special-native-1790660793795` 只落一条账号2事件。它验证实际观察函数的原生边界；快速反复切换和旧账号计时器精确边界由上两层确定性测试覆盖，不声称每个组合均由人工原生切换复现。

**相似资源页面专项通过：**实际Vite 15173→Flask 15000→隔离库 `resource_chain_7a54fb93b0d4_test`。只新增合成资源91001–91006及其测试标签/身份/字段证据，未复制日常数据。源91001、确认别名91003、下架91004均不返回；同域不同路径的付费产品91002与未知收费91005保留。显示共同标签、完全免费与付费差异、收费待核实。首次合成字段未带验证时间时显示“未知”符合规则，补齐合成证据时间后正确显示收费差异。

- 从详情相似卡片“查看详情”进入91002，标题和内容最终正确；“访问网站”实际新开本机 `/fixture/91002`，未访问外部产品。路由最初误判来自动画过渡与标题内部重复文本，校正状态断言后通过；没有保留多余路由修改。
- 91006真实空结果显示“暂无相似网站”。仅对similar请求注入网络abort，页面提示失败；解除后点重试，真实响应恢复。未伪造成功/空结果HTTP响应。
- 账号1（research_fixture）在相似卡片收藏91002；真实退出并用表单登录账号2（api_fixture）后仍显示“添加收藏”；切回账号1显示“取消收藏”，再取消恢复测试前状态。最终数据库该资源收藏为空。
- 1440×1000、390×844逐卡片滚动验证：实际opacity>0.999、理由未截断、无横向溢出、全部操作控件中心命中自身。已目视检查 `similar-desktop-final-0.png`、`similar-narrow-final-0.png`；每张卡片另有 `*-final-1.png`。浮动AI入口沿用原布局，卡片滚至阅读位置时收费理由、收藏、访问和详情入口可用。不是所有滚动位置和全站动画的重新验收。

本轮唯一产品修改文件为 `backend/frontend/src/views/SiteDetail.vue`，在原有未提交修改上追加三个具体修复：similar失败提示/重试；绑定并清理相似卡片渐入观察器（此前DOM存在但opacity恒为0）；只取消相似页理由的两行截断以完整显示收费差异。保留原网格、公共样式、动画时长和其他页面行为。回归为本专项浏览器脚本、可控时钟检查与最终 `npm run build --prefix backend/frontend`（2659模块，7.24秒），未重跑整套后端/前端测试。

主要附件：`special-browser-log.json`（实际操作、失败诊断及最终断言，按顺序保留）、`similar-visual-final.json`、`special-final-audit.json`、上述三个曝光JSON及截图。可复核脚本为 `verify-visibility-boundaries.mjs`、`verify_special_browser.py`、`verify_similar_visual.py`、`verify_native_visibility_browser.py`、`audit_special_acceptance.py`；浏览器脚本通过现有agent-browser CLI，不引入产品依赖。环境恢复后可用 `SPECIAL_BROWSER_SESSION` 选择已连接的独立测试会话。

### 必需验收与附件边界

已保存5fps录屏 `special.webm`、`special-fixed.webm`、`similar-visual-final.webm`，分别覆盖初始操作、修复中操作和最终视觉专项。长账号操作录制停止时报 `Recording encoder fell behind by more than 16 buffered frames`，不能声称有本次从头到尾的完整视频。该失败和额度导致的中断已记录，未反复重试长录制。之前的空白卡片截图保留为缺陷证据，最终以带 `final-0/1` 的截图为准。

功能必需项由真实页面、确定性断言、原生时序和数据库证据支撑；完整视频是附件，**不作为全部功能启用的阻碍**，5fps也不证明全帧率动画流畅度。真实模型仍未验收，与视频无关。

### 日常环境的实际三类状态

只读核查时间见 `artifacts/local-integration/special-final-audit.json`、`daily-readonly-audit.json`。实际本机数据源为 **127.0.0.1:3306/nav_site**，数据库连接用户root；`backend/.env` 存在。根 `.env` 是另一套Compose配置，不能因同名nav_site就视为同一个数据库；Compose默认是容器MySQL、宿主3307。本次未迁移到Compose。

| 分类 | 实际状态及范围 |
| --- | --- |
| 1. 已在日常环境生效 | 既有MySQL与nav_site数据保留；233条旧行为记录未改动。当前未确认日常Web进程，复核5000/5173无监听，不能列任何新增Web功能为“已经在线启用”。原有代码具备登录/问卷/职业推荐/收藏等能力不等于当前服务已运行。 |
| 2. 已验证、需启动/迁移/配置 | 登录、问卷、职业切换、普通数据库检索、收藏、规则AI降级、相似页可按下方本机基线启动；无需模型密钥。Meili同步、Redis缓存、负反馈和新版曝光已隔离验证，但日常迁移表/worker/开关未生效，需要按顺序审阅执行。 |
| 3. 必须关闭或待审 | 16条身份未决继续隔离；本次标签预览仍29待新增、1已有，29不落库。行为实验继续关闭；新重排默认0。反馈、新版曝光在日常仍0，直到迁移及测试账号名单核准。真实模型缺凭据，模型增强能力未验收，日常先明确关闭模型调用。 |

实际进程环境及backend/.env未设置 `SEARCH_BACKEND`、`SEARCH_SYNC_ENABLED`、`RECOMMENDATION_FEEDBACK_ENABLED`、`RECOMMENDATION_RERANK_ENABLED`、`RECOMMENDATION_EXPOSURE_V2`；后三者代码默认0，搜索代码默认Meili不代表Meili服务已可用。日常 `resource_field_claims`、`resource_identity_links`、`resource_quality_changes`、`outbox_events`、`search_sync_state`、`recommendation_feedback_migrations`、`recommendation_preferences` 均不存在。未把隔离通过推断为日常生效。

### 可审阅的执行顺序（本轮未执行任何日常写入或启动）

**A. 先启用已有数据库基线。** 目标保持127.0.0.1:3306/nav_site，不运行 `local_integration.py prepare`，不把业务库伪装为`*_test`。先由操作者在本机确认备份目录和凭据；不在聊天发送密钥。以下从仓库根目录执行，密钥只在终端交互/本机环境设置：

```powershell
# 一次性配置本机登录项；密码交互输入，不写命令行
mysql_config_editor set --login-path=zhihangyu-daily --host=127.0.0.1 --port=3306 --user=root --password
mysql --login-path=zhihangyu-daily --database=nav_site --execute="SELECT DATABASE(),@@port;"
$backupDir = Join-Path $env:LOCALAPPDATA ('zhihangyu-backups/' + (Get-Date -Format yyyyMMdd-HHmmss))
New-Item -ItemType Directory -Path $backupDir
Copy-Item -LiteralPath backend/.env -Destination (Join-Path $backupDir 'backend.env')
$backupFile = Join-Path $backupDir 'nav_site.sql'
mysqldump --login-path=zhihangyu-daily --single-transaction --routines --triggers --events --hex-blob --no-tablespaces --set-gtid-purged=OFF --result-file=$backupFile nav_site
if ($LASTEXITCODE -ne 0) { throw 'Backup failed; stop activation' }
Get-FileHash -Algorithm SHA256 -LiteralPath $backupFile
```

备份不入Git；维护期间停止应用/导入/爬虫等写入者，避免DDL破坏一致性。先把dump恢复到新建的 `nav_site_restore_check` 空库核对表数、资源/用户/收藏数和233旧事件；dump不带`--databases`，避免内含`USE nav_site`。恢复命令为 `mysql --login-path=zhihangyu-daily --execute="CREATE DATABASE nav_site_restore_check CHARACTER SET utf8mb4;"`，再 `mysql --login-path=zhihangyu-daily --database=nav_site_restore_check --execute="source $backupFile"`。已有同名恢复库则换新名字，不能覆盖。恢复核对未通过就不迁移。

日常基线启动终端（将这些非密钥配置同步到backend/.env后可免每次输入；本轮文件未改）：

```powershell
$env:MYSQL_HOST='127.0.0.1'; $env:MYSQL_PORT='3306'; $env:MYSQL_DATABASE='nav_site'
$env:SEARCH_BACKEND='database'; $env:SEARCH_SYNC_ENABLED='0'
$env:RECOMMENDATION_FEEDBACK_ENABLED='0'; $env:RECOMMENDATION_EXPOSURE_V2='0'
$env:RECOMMENDATION_RERANK_ENABLED='0'; $env:AI_REQUIREMENTS_MODEL_ENABLED='0'
$env:FLASK_DEBUG='0'
python -m flask --app backend/app.py run --host 127.0.0.1 --port 5000 --no-reload
# 另一个终端
$env:API_PROXY_TARGET='http://127.0.0.1:5000'
npm run dev --prefix backend/frontend -- --host 127.0.0.1 --port 5173 --strictPort
```

选择Flask导入入口是为避免 `python backend/app.py` 的 `__main__` 自动初始化/同步种子分类资源及启动定时爬虫；这条基线启动命令不执行该main分支，也不启用定时任务。成功判据：健康接口连接nav_site，页面可登录/检索/收藏/显示相似资源；缺模型时规则检索与降级提示可用，三个推荐开关仍0。停服务即可回到本轮未启动状态，配置用备份恢复；无需重建或恢复数据库。

**B. 再准备可选搜索索引和缓存。** 仍使用本机nav_site；拟用独立新索引 `websites_daily_v1`，Meili `http://127.0.0.1:7700`，Redis `redis://127.0.0.1:6379/6`。与隔离17700/16379、Redis /7、`stage2_test_*`分开。先检查端口/容器名没有被其他服务占用。没有现有实例时，以下仅为待批准的本地服务命令：

```powershell
# 在本机环境中提供MEILI_MASTER_KEY，沿用私密配置，不粘贴到报告/聊天
docker run -d --name zhihangyu-daily-meili -p 127.0.0.1:7700:7700 -e MEILI_MASTER_KEY -e MEILI_NO_ANALYTICS=true -v zhihangyu_daily_meili:/meili_data getmeili/meilisearch:v1.12.8
docker run -d --name zhihangyu-daily-redis -p 127.0.0.1:6379:6379 -v zhihangyu_daily_redis:/data redis:7.4.11 redis-server --appendonly yes
```

若具名容器已存在，先检查挂载/端口/用途后仅start，不能重复run或删除已有卷。目标连接值写backend/.env，应用和worker使用同一组 `MEILI_HOST`、`MEILI_MASTER_KEY`、`MEILI_INDEX=websites_daily_v1`、`REDIS_URL`。缓存键已经包含数据库/索引/版本，不存在需要另设的虚构namespace变量。基线应用继续`SEARCH_BACKEND=database`直到索引对账通过。

**C. 审阅迁移，先追溯表，再搜索触发器。** 当前只读预览附件为 `daily-search-migration-preview.json`、`daily-feedback-preview.json`、`daily-tags-preview.json`。搜索预览明确缺两张可选追溯表，因此它不能直接当最终迁移计划；先审阅并只应用 `backend/sql/migrations/20260924_resource_quality.up.sql` 的三张空追溯表，不应用标签/身份数据。SQL执行前核对备份恢复成功、目标SELECT DATABASE()为nav_site：

```powershell
mysql --login-path=zhihangyu-daily --database=nav_site --execute="source backend/sql/migrations/20260924_resource_quality.up.sql"
python backend/scripts/search_sync.py migration-preview --output artifacts/local-integration/daily-search-migration-approved.json
python backend/scripts/search_sync.py migration-rollback-preview --output artifacts/local-integration/daily-search-rollback-approved.json
```

重新预览必须包含7张受保护表（websites、tags、site_tags、site_occupations、categories、resource_field_claims、resource_identity_links），且missing_optional_tables为空。**现有三个迁移CLI只允许隔离库写入，search_sync还禁止业务索引initialize/rebuild/retry；不能把早期报告里的`--test-database`命令改库名后用于nav_site。** 以下是管理员审阅后用MySQL客户端执行预览SQL的具体方案，没有解除产品CLI保护：

```powershell
$plan = Get-Content -Raw artifacts/local-integration/daily-search-migration-approved.json | ConvertFrom-Json
if ($plan.database -ne 'nav_site' -or $plan.missing_optional_tables.Count -ne 0) { throw 'Wrong/incomplete target preview' }
$sql = 'USE nav_site;' + "`n" + 'DELIMITER $$' + "`n" + $plan.outbox_table + '$$' + "`n" + (($plan.statements | ForEach-Object { $_ + '$$' + "`n" }) -join '') + "DELIMITER ;`n"
$sql | Set-Content -Encoding utf8 artifacts/local-integration/daily-search-reviewed.sql
# 先审阅生成的SQL；冻结写入，重新预览确认无漂移，再由操作者执行
mysql --login-path=zhihangyu-daily --database=nav_site --execute="source artifacts/local-integration/daily-search-reviewed.sql"
```

成功判据：search_sync_state有id=1；原outbox模型表存在；全部21个本版触发器存在；旧资源/收藏/233行为记录不变。MySQL DDL有隐式提交，不能声称整份迁移可事务撤销。失败停worker、保持数据库检索，生成新的回滚预览，只移除本版触发器；追溯表/队列/历史不删除。

**D. 初始化独立索引→临时重建/对账→worker→读取切换。** 因现有业务维护CLI门禁，以下为待审的操作者Python片段，显式确认目标后调用现有维护实现；不修改CLI、不使用测试库参数，不自动执行。必须在C成功之后，且同一终端已设置上述目标环境：

```powershell
@'
import sys,os,json
sys.path[:0]=['backend','.']
from search_catalog import Catalog,engine_from_environment
from search_service import Meili
from search_sync import Sync
engine=engine_from_environment()
assert (engine.url.host,engine.url.port,engine.url.database)==('127.0.0.1',3306,'nav_site')
assert os.environ['MEILI_INDEX']=='websites_daily_v1'
sync=Sync(Catalog(engine),Meili(os.environ['MEILI_HOST'],os.environ['MEILI_MASTER_KEY'],os.environ['MEILI_INDEX']))
# 仅首次初始化；索引已存在时报错停下检查，不删除、不盲目重复创建
with sync.lock():
    sync.task('POST','/indexes',{'uid':sync.meili.index,'primaryKey':'id'},target=sync.meili.index)
print(json.dumps(sync.rebuild(),default=str))
print(json.dumps(sync.reconcile(),default=str))
'@ | python -
python backend/scripts/search_sync.py reconcile
python backend/scripts/search_sync.py status
# 独立worker终端，与应用保持同一数据库/Meili/Redis配置
$env:SEARCH_SYNC_ENABLED='1'
python backend/scripts/search_sync.py worker
```

reconcile的missing/stale/not_public_or_removed均空、任务succeeded、revision/indexed_revision一致、outbox收敛且dead=0后，才把应用的`SEARCH_BACKEND=meilisearch`并重启上述Flask读取进程。一次冷/热查询结果一致即达成功判据，无需重复已通过整套测试。Redis不可用允许无缓存运行；Meili失败优先`SEARCH_BACKEND=database`并重启读取进程，再停本次worker，保留新索引/队列/last_error诊断；不swap旧索引当作最新数据，不删卷。索引初始化/重建失败时保持基线；retry/recover也需另审业务维护操作，不能直接套隔离CLI。

**E. 反馈/新版曝光分开批准，重排不在本方案中开启。** 反馈预览的三条CREATE TABLE可单独审阅应用，激活门禁SQL为 `INSERT INTO recommendation_feedback_migrations(version,active) VALUES('20260926_feedback_v1',1) ON DUPLICATE KEY UPDATE active=1;`。执行前确认user_behavior_events存在、A步骤备份有效；不更改233历史事件。迁移本身不启用反馈。后续明确批准才设置backend/.env `RECOMMENDATION_FEEDBACK_ENABLED=1`并重启；新版曝光无需新事件表，但先核准 `RECOMMENDATION_METRICS_TEST_USER_IDS` 的业务测试账号ID名单，再单独批准 `RECOMMENDATION_EXPOSURE_V2=1`。本轮以及初次基线均保持0。成功判据为新请求归属当前账号、反馈门禁active及新版事件时间/位置完整；恢复时两个开关归0、重启，门禁active=0，保留偏好/审计。不新增行为实验、不开启重排。

```powershell
python backend/scripts/feedback_migration.py preview --output artifacts/local-integration/daily-feedback-approved.json
$feedbackPlan = Get-Content -Raw artifacts/local-integration/daily-feedback-approved.json | ConvertFrom-Json
if ($feedbackPlan.version -ne '20260926_feedback_v1') { throw 'Unexpected feedback migration' }
$feedbackSql = (($feedbackPlan.statements | Where-Object { $_ -like 'CREATE TABLE*' } | ForEach-Object { $_ + ';' }) -join "`n") + "`nINSERT INTO recommendation_feedback_migrations(version,active) VALUES('20260926_feedback_v1',1) ON DUPLICATE KEY UPDATE active=1;"
$feedbackSql | Set-Content -Encoding utf8 artifacts/local-integration/daily-feedback-reviewed.sql
# 审阅SQL后才由操作者执行；两个功能开关此时仍为0
mysql --login-path=zhihangyu-daily --database=nav_site --execute="source artifacts/local-integration/daily-feedback-reviewed.sql"
# 回退门禁（先关闭开关并重启应用）
mysql --login-path=zhihangyu-daily --database=nav_site --execute="UPDATE recommendation_feedback_migrations SET active=0 WHERE version='20260926_feedback_v1';"
```

### 真实模型及最终执行清单

`DEEPSEEK_API_KEY` 在当前环境/backend/.env仍缺失；`AI_REQUIREMENTS_MODEL_ENABLED`代码默认1，建议基线显式0。授权后由操作者在 **backend/.env或启动进程环境** 配置真实key并设模型开关1，不在聊天发送。现有客户端固定 `https://api.deepseek.com/chat/completions` / `deepseek-chat`，没有虚构的模型地址变量。规则检索、结构化条件和错误降级已经可用，不依赖模型凭据；增强理解/模型解释仍未验收，未重复模拟联调。

```powershell
# 凭据配置后，沿用已有隔离库，最多10次真实调用
python backend/scripts/verify_stage3_real_model.py --run --database ai_retrieval_80183efd0298_test --output docs/release/real-model.json
```

- **现在能用什么：** 经专项及既有隔离证据验证的登录/问卷/职业推荐/数据库检索/收藏/规则AI降级/相似页；按A启动才成为日常可用服务。不能称日常已经全开。
- **还差什么：** 对日常执行A–E的审阅与授权、备份恢复核对、业务迁移/新索引/worker配置、真实模型凭据和联调；16身份与29关联仍待审，行为实验与重排继续关闭。视频不构成功能阻碍。
- **下一步命令：** 先A的备份和基线启动；需要索引时再B→C重新预览→D初始化/对账/worker；反馈和新版曝光只在E单独批准后开启。日常配置未改，所有未来写入命令仅供审阅。

最终清理：恢复工作后启动的隔离Flask（PID13000）、Vite（PID30572/27668）和专用Chrome（PID58000，核对 `zhihangyu-special-final-chrome` 与19223）已停止。最终15000/15173/19223无监听，用户MySQL3306/PID50708继续运行；未启动或停止日常Compose栈、未删除容器/卷/数据库。合成测试数据和附件保留。第一次恢复后的about:blank截图不作页面证据；有效视觉证据仅为 `similar-*-final-0/1.png`。所有原有未提交修改保留。


更新：2026-09-29（Asia/Shanghai）。本轮完成集成缺陷修复、隔离验证和启用清单；**不是正式启用，也不是全部发布验收通过**。没有推送、部署、正式标签落库或行为推荐实验。工作区原有修改保留。

## 9月29日收尾结果（优先于下文早期执行记录）

### 已修复并验证

- 真实浏览器复现了收藏跨账号污染：A 添加资源49的响应被保持，退出并登录B后再释放，B的前端收藏与缓存被错误更新；数据库仍属于A。修复 `backend/frontend/src/utils/api.js` 的请求令牌归属检查，以及 `backend/frontend/src/stores/favorites.js` 的账号/会话代际校验，覆盖加载、增删、错误恢复、后台同步和缓存写入。缓存版本升为2，避免沿用此前污染的本机缓存，不删除数据库收藏。页面布局、动画及服务端JWT鉴权未变。
- 新增 `verify-favorite-account-race.mjs` 执行实际函数；原 `verify-site-favorites.mjs` 的无条件 finally 源码检查改为调用该业务验证：本账号完成必须清 pending，旧账号完成不能清新账号 pending，断言保护增强，没有跳过原目标。
- `integration_response_gate.py` 仅由隔离启动参数 `--response-gates` 安装，在真实后端完成鉴权/处理后保持响应，文件明确释放，不随机等待、不模拟返回内容。浏览器探针只记录安全的路径、时间、状态和资源ID；测试XHR超时延长至300秒，产品超时未改变。
- `artifacts/local-integration/gates/` 的 account-b-after、favorite-fixed-after、undo-after、career-fixed-after 均 `same:true`。A反馈及推荐响应保持期间通过真实SPA退出/登录B，B响应先完成，A于 2026-09-28 14:29:29 UTC 后返回；列表、收藏、偏好、pending、撤销和错误状态未被更新。另覆盖收藏迟到、撤销迟到和Python职业请求晚于后端工程师请求返回。`race-summary.json` 汇总浏览器起止时间，`events.jsonl` 保留后端 held/released/sent 时间；进程重启后的 sequence 重新计数，跨进程比较使用UTC时间。原 favorite-after-defect.json 保留失败证据。
- Docker当前阻碍为进程停止，而非已确认的持续 dockerInference 故障。9月28日恢复后实际完成同步链路；9月29日再次检查无Desktop进程/引擎管道，启动已安装Desktop一次即成功，Engine 29.4.2。只启动具名隔离Redis/Meili容器，分别 PONG / available，隔离worker可启动。没有修改Docker配置、重置WSL、删除卷或重启用户MySQL。依据 [Docker故障诊断](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/) 和 [WSL后端说明](https://docs.docker.com/desktop/features/wsl/) 先确认运行状态；未找到可直接套用的同版本官方 dockerInference 修复记录，没有猜测性更改设置。
- `sync-recovery.json` 为真实 MySQL→outbox→Meili→Redis→HTTP/浏览器链路：停止worker后修改合成资源49，待同步期间数据库叠加检索可见；重启worker后Meili命中、热缓存命中；下架立即从返回结果消失，消费后索引404。最终恢复原始合成摘要与审核状态。截图为 sync-index-result.png / sync-after-unpublish.png。测试脚本的错误断言及Windows编码恢复问题已修正，并在JSON中保留说明，不作为产品故障隐藏。

### 已验证、待实际启用

公共搜索、同步worker、缓存失效、反馈及新曝光已具备上述隔离证据；业务库迁移、正式worker及新策略仍未启用。默认 `RECOMMENDATION_FEEDBACK_ENABLED`、`RECOMMENDATION_RERANK_ENABLED`、`RECOMMENDATION_EXPOSURE_V2` 继续为0。默认关闭的基线证据仍见 baseline-rollback.json。启动顺序沿用下文：审阅迁移→应用到授权目标→初始化/对账索引→worker→应用；失败优先停新开关并回数据库检索，不清在线索引。

桌面1440×1000和窄屏390×844真实点击菜单、暂时不需要、撤销；桌面另点击换批。只读rAF几何采样每至少50ms一次，分别57/51帧，菜单可见17/16帧；横向溢出、菜单越界、按钮中心被遮挡均0。已查看 dynamic-desktop-menu-final.png、dynamic-desktop-final.png、dynamic-narrow-menu.png、dynamic-narrow-restored.png；菜单可操作、恢复后的卡片排列正常，保留现有渐入动画。窄屏首次截图中的合成摘要乱码来自测试恢复脚本编码，修正UTF-8并刷新后的截图正常；不是修改真实资源数据。

本次必要回归实际执行：AI七字段错误契约20项；stage4后端10项；浏览历史13项；前端收藏20项、职业切换59项、账号请求契约、收藏统一状态、stage4反馈/曝光检查及新增收藏竞态均通过。前端 `npm run build` 成功（2659模块，10.70秒）。命令：`python -m unittest discover -s tests -p test_ai_site_recommend_v1.py`、同目录 `test_recommendation_stage4.py`；`node backend/frontend/scripts/verify-{browsing-history,site-favorites,favorite-account-race,favorite-state-unification,auth-request-contract,stage4-feedback,career-switching}.mjs`（花括号为文件列举，PowerShell请逐条运行）。

9月29日只读复核隔离事件：178 impression、4 click、4 favorite、9 feedback、6 feedback_undo；visible-v2账号2为100、账号1为54，缺时间/位置0、重复曝光0、离屏批次曝光0；2个新版点击均可关联同账号/批次/位置曝光，其中1个曝光先于点击。不能把稍后才达到可见阈值的曝光冒充点击前曝光。明确排除合成账号1–4后事件为0。业务库233条缺字段历史事件未修改，不混入新版依赖时间/位置指标。

### 仍需凭据或人工判断

9月29日检查当前进程环境和 `backend/.env`，`DEEPSEEK_API_KEY` 仍缺失，未输出配置值。真实联调未执行；现有命令与配置见下文，无需重复模拟测试代替凭据。16条身份未决继续隔离，29条待新增标签不正式落库；业务测试账号名单仍需可靠配置确认。不能进行行为推荐实验。

### 因环境限制未完成及验收边界

完整视频录制报 `Recording encoder fell behind by more than 16 buffered frames`；后续旧控制会话报 `os error 10060`，更换CLI控制会话后截图/真实操作恢复。原contact sheet只有两个初始帧，不能证明动画全程。上述真实点击和连续几何采样已执行，但不宣称完整帧率/动画流畅度验收。亚秒切后台阈值竞态、相似页专门浏览器操作仍无新增证据；已有后台切换和函数检查不能替代这两项。需要在可持续录屏的浏览器环境补验，保留此范围，不反复尝试同一失败录制。

当前可用范围是代码与隔离环境中的登录、问卷、职业切换、搜索、收藏、规则AI回退、反馈与同步；不代表业务环境全面启用。截图与JSON均在 `artifacts/local-integration/`，与真实行为库隔离。

## 早期集成记录与证据边界（9月27–28日上午）

正式前端入口为 `backend/frontend` 的 Vite 应用，后端入口为 `backend/app.py`。本轮浏览器通过 Vite 15173 代理 Flask 15000，使用真实路由、JWT、MySQL；数据库为 `resource_chain_7a54fb93b0d4_test`，4 个合成账号、43 条合成资源。账号来自测试脚本，不靠用户名猜测真实账号身份。没有复制真实用户、密码、收藏或行为。

9 月 27 日独立服务验证使用本机 MySQL 9.7.1、Docker Meilisearch 1.12.8（17700）、Redis 7.4.11（16379），结果保存在 [search-sync.json](search-sync.json)。9 月 28 日 Docker Engine 未能启动，浏览器验收走数据库故障降级与无缓存路径。不能将前者的服务级成功描述为后者的浏览器索引联调成功。

业务库 `nav_site` 仅做只读审计和标签预览，不作为测试库。[最终只读审计](current-readiness-audit-final.json)仍为 233 条历史事件，均缺时间和位置。实际开关环境未设置，搜索 outbox、同步状态、身份追溯及反馈迁移表尚未建立，不能宣称正式迁移完成。正式应用进程与生产拓扑未获确认。

验收服务初版曾因 `db_pool` 导入时缓存配置，导致最初只读页面请求读取原库目录；在登录、收藏、反馈等浏览器写入之前已停止并修复。现在设置隔离环境后重新加载连接池，并在导入 app 前用 `SELECT DATABASE()` 验证实际连接。该次只读页面不计入隔离验收。又发现 Windows 遗留测试进程会干扰开关验证，已增加 15000 端口占用即拒绝启动的检查；停止时核对完整测试命令与 PID。

## 功能实际状态

“隔离通过”仅指下面具体证据，不代表在业务库生效。退出本轮测试后测试应用不继续运行。

| 功能 | 代码/迁移 | 正式运行与开关 | 已完成验收 | 剩余条件 |
| --- | --- | --- | --- | --- |
| 资源字段与标签 | 复用现有字段，质量/身份/标签工具已实现；业务库追溯迁移未应用 | 现有资源字段可读；新批次未生效 | 资源链路 40 项；标签隔离迁移/重复执行/回滚 12 项 | 16 条身份人工核实；29 个待新增关联保持待审阅、未应用 |
| 公共搜索 | 公共 SearchService 已接入；同步迁移仅隔离应用 | 业务环境 SEARCH_BACKEND 未设置，代码默认 Meili；实际在线服务未确认 | 名称/别名/用途/标签、筛选、分页；浏览器真实数据库降级 | 业务库迁移、索引重建与对账后再切流 |
| outbox/索引同步 | 同事务触发器和原 outbox 消费器；仅隔离迁移 | SEARCH_SYNC_ENABLED 未设置；search-worker 为 Compose 可选 profile | 85 项中包含提交/回滚、重复、乱序、租约/重启、任务确认、重建增量 | Docker 已恢复，隔离重启链路通过；业务迁移审阅及正式 worker 未启用 |
| Redis 缓存失效 | 查询维度和数据库/索引版本缓存 | 业务 Redis 运行未确认；隔离 Redis 已恢复并验证 | 独立 Redis 冷热缓存及更新验证；浏览器无缓存仍可搜索 | 隔离写入→索引→缓存→浏览器已补齐；待授权业务启用 |
| AI 结构化检索 | 服务端结构验证/规则回退及前端条件展示已完成 | 模型开关默认 1；DEEPSEEK_API_KEY 缺失，真实模型未调用 | 七字段错误接口 20 项；真实页面条件/未知/降级提示 | 授权凭据后运行现有小规模联调；不能声称模型准确率验收 |
| 相似资源 | 任务/标签/类别/条件基线已实现，无独立迁移 | 随应用代码运行，正式部署未确认 | 前三阶段既有隔离用例 | 本轮未追加相似页浏览器点击验收 |
| 负反馈 | 偏好、幂等操作及审计代码；隔离迁移已应用 | RECOMMENDATION_FEEDBACK_ENABLED 默认 0 | 三类反馈、即时撤销、设置恢复、失败恢复、换账号；状态写入真实隔离库 | 精确 SPA 迟到时序已补齐并修复收藏污染；待授权迁移/启用 |
| 多样性重排 | 独立策略，原匹配分数/权重保留 | RECOMMENDATION_RERANK_ENABLED 默认 0 | 隔离开启、同产品去重、换批；关闭后 21 候选/8 卡片正常 | 继续默认关闭，不因测试自动推广 |
| 新行为采集 | visible-v2/server-time-v1，复用原事件表 | RECOMMENDATION_EXPOSURE_V2 默认 0 | 真实滚动、后台切换、跨账号、点击上下文及落库；版本分开统计 | 核实正式测试账号清单，积累新数据；亚秒切后台时序及动画完整验收仍待完成 |

## 本次修改与原因

1. `backend/frontend/src/views/Home.vue`：候选池之前用域名去重，同域不同产品被压成少量卡片，影响换批。改为已确认 canonical_site_id / 资源 ID，缺 ID 时保留完整 URL，路径不转小写。新增执行真实函数的 17 条同域产品/跨批/别名/大小写回归。
2. `backend/v1_routes.py`：分类列表对旧 NULL code 返回生成代码，但搜索不接受该代码，真实选择 Test resources 返回 400。现在只接受唯一的、确实无原 code 的对应分类；重名生成冲突拒绝，不覆盖已有 code。
3. `behaviorTracker.js`、`siteVisit.js`：职业卡片访问原 click 接口遗漏 visible-v2、位置、算法与重排版本。复用同一 context 给原点击请求，不新增第二条 click。搜索点击不伪造推荐曝光上下文。
4. `stop.bat`：`docker compose --profile search-sync down` 同时停止曾显式启动的 worker；不删除数据卷，start.bat 默认启动方式不变。Compose 静态配置确认包含六项服务；实际 down 受引擎故障限制，未对用户服务执行。
5. `backend/scripts/local_integration.py`：仅限当前 manifest 指定的本机测试库，连接池/端口保护；提供可选 0–30 秒反馈 POST 延迟供隔离故障注入。没有向产品路由加入延迟。
6. `backend/scripts/audit_local_integration_events.py`：只读指定测试库，按用户、批次、位置、版本复核，不生成事件。新增 `tests/test_integration_category_contract.py`、前端 `verify-integration-regressions.mjs`。

## 真实浏览器验收

原 CUA 连接报 `nodeRepl.fetch request failed`。替代方案已经实际可用：系统 Chrome 独立 headless 进程、独立用户目录、CDP 19223；复用 agent-browser 0.38.1 CLI。未增加产品依赖。以下操作是真实页面+隔离后端，非模板回放。

| 操作 | 结果与范围 |
| --- | --- |
| 登录、退出、账号切换 | 使用合成表单账号 api_fixture/research_fixture 完成；收藏及偏好按账号隔离 |
| 问卷 | 完整点击职业→后端→Python→API任务/痛点/主要需求→经验/工具目标/偏好/平台/预算/协作→提交。数据库 V3 保存 developer/backend/api_debugging；从研究生资源变为后端/API资源，见 [持久化证据](browser-questionnaire.json) |
| 职业切换、换批 | 研究生/研究人员切换；换批返回另一组 ID；修复域名去重后可正常换批，不以标题变化代替资源变化 |
| 搜索建议、筛选、分页 | 输入“接口”返回 5 条真实 Fixture 建议；“接口调试”21 条，Test resources 筛选成功，第二页只有 API Fixture，前后分页状态正确 |
| AI | 输入免费、中文、无需安装、新手的接口调试需求；展示五项条件、缺失字段待核实、没有完全符合以及降级提示；模型调用 0 次。部分匹配/澄清等其他分支见既有模拟回归，不冒充本轮浏览器覆盖 |
| 收藏和跳转 | 实际收藏 Fixture 11，换账号状态独立；点击本机 `/fixture/11` 新标签页打开。没有访问外部真实产品或修改真实收藏 |
| 三类反馈、撤销/恢复 | 不相关、已经知道、暂时不需要均由真实 UI 提交；即时撤销、设置页“恢复推荐”写入隔离库，原收藏保留 |
| 失败恢复 | CLI 对反馈接口 abort（明确为网络故障注入），页面恢复卡片并给出重试；解除拦截后可重试。不是模拟成功响应 |
| 慢请求 | 隔离服务延迟 POST 30 秒，真实点击、退出、另账号登录；旧偏好仅写原账号。第一次切换包含页面重新导航；第二次 SPA 操作受工具调度等待影响，未证明“新账号已登录后才返回”的精确时序。函数级 epoch/乱序回归已通过，不能替代该浏览器子场景 |
| 可见曝光 | 未滚入视口批次曝光 0；同账号同批次没有重复；两个账号各有 visible-v2；原生后台约25秒新增曝光0，见 [后台证据](browser-background.json)。该次使用已曝光卡片，不能替代隐藏发生在1000ms阈值之前的竞争测试 |
| 开关关闭 | 停止旧测试进程，以不带 --new-policy 重启，API 21 条职业候选，页面8卡片、0反馈菜单，搜索200，见 [回退证据](baseline-rollback.json) |

截图位于 `artifacts/local-integration/`：`desktop-feedback.png`、`desktop-settings.png`、`desktop-search.png`、`desktop-ai.png`（1440×1000）；`narrow-feedback.png`、`narrow-ai.png`、`narrow-baseline.png`（390×844）。已查看前六张相关截图：菜单在卡片和视口内、设置恢复入口可见、AI 条件及提示可见，窄屏 DOM 无横向溢出。首次 narrow-feedback 捕获加载中，已用稳定菜单截图覆盖。首页初始截图为小视口，不当作桌面证据。

保持原动画实现。本轮看到正常加载/路由过渡并等待稳定截图，但没有录制逐帧动画或覆盖全部滚动/固定头部交叠；不能宣称完整动态视觉验收。

## 新事件链路与历史数据

[浏览器事件审计](browser-events.json)可通过 `python backend/scripts/audit_local_integration_events.py` 重现。09:22:25 最后快照：曝光105、点击4、收藏2、反馈5、撤销2。曝光中 visible-v2 为81（账号2为65、账号1为16）；其余24为关闭新开关时的旧口径，分开保留。

- visible-v2 时间/位置缺失0、同用户/资源/批次/session重复曝光0；测试账号1–4显式排除后事件0。该排除名单只适用于合成测试库，不推断业务库账号。
- 位置为当前实际显示批次内 **1起始** 编号，带 `display-position-v1`；阈值≥50%连续1000ms，后台/卸载重置。批次包含职业、批号、响应式页大小。
- 修复后两条点击均带实际资源/账号/批次/位置/版本，均能关联同批次曝光；其中1条曝光发生在点击之后1秒，不能算“先曝光后点击”。另一条在已曝光后点击，时间顺序可用。不补造提前曝光。
- 修复前测试点击保留旧口径，搜索点击没有推荐批次属于预期，不能混算推荐 CTR。反馈/撤销独立事件不算点击/收藏。
- 业务库233条历史事件不回填、不删除。可做缺失质量盘点及有限总量统计；不能用于依赖时间窗口、展示位置、可见率、先曝光后点击的趋势/CTR，也不能重建历史画像或认定实验门槛满足。

## 本轮执行的验证

| 命令/证据 | 实际结果 |
| --- | --- |
| `python backend/scripts/verify_resource_chain.py` → resource-chain.json（9月27日） | 40项，真实隔离MySQL：问卷/画像/职业资源/理由、V2、空画像、鉴权、收藏、分页、迁移回滚 |
| `python backend/scripts/verify_v3_tag_identity_migration.py` → tag-migration.json（9月27日） | 12项；28条新增，测试夹具额外预置1条关联，故比业务预览29少1；重复幂等，回滚仅撤销本版本，4646条既有关联受保护 |
| `python backend/scripts/verify_search_sync.py` → search-sync.json（9月27日） | 85项；8资源固定夹具（6公开）、固定查询/冷热缓存，记录本地耗时；更新/下架/故障降级/重建/重启。不代表生产性能 |
| `python -m unittest discover -s tests -p test_integration_category_contract.py` | 3项，生成分类代码、歧义拒绝、显式代码不被别名覆盖 |
| 同上，`test_site_search_v1.py` | 11项普通搜索 |
| 同上，`test_ai_site_recommend_v1.py` | 20项，含七字段错误与正常成功兼容 |
| 同上，`test_docker_entrypoint.py` | 3项，已有库不被启动初始化 |
| `node backend/frontend/scripts/verify-integration-regressions.mjs` | 候选跨批身份、别名、路径大小写、单次点击及实际上下文通过 |
| `verify-stage5-collection.mjs`、`verify-browsing-history.mjs` | 账号去重/位置、13组浏览历史检查通过 |
| `verify-stage4-feedback.mjs` | store失败恢复/撤销/换号/乱序/到期、可见计时、分页函数回放通过（非浏览器） |
| `verify-career-switching.mjs`、`verify-favorite-state-unification.mjs` | 59项职业流、收藏统一状态通过 |
| `verify-ai-error-contract.mjs` | 11个前端响应场景回放通过 |
| `npm run build`，目录 backend/frontend | 2659模块构建成功（9月28日），未部署 |
| `python -m py_compile backend/scripts/local_integration.py backend/scripts/audit_local_integration_events.py` | 语法通过；新增延迟参数后再次检查 |
| `docker compose --profile search-sync config --services` | mysql/redis/meilisearch/backend/frontend/search-worker；引擎未运行不妨碍配置校验 |

检查曾出现的测试夹具导入/SQL别名错误已修正后重跑通过，没有删减既有断言。没有反复扩大全量测试或用模拟事件充当真实行为积累。

## 迁移与启用顺序、成功判据、恢复

以下是启用准备，**不是授权在业务库直接执行**。现有维护CLI故意限制写入本机 `_test` 库，不得绕过检查或把业务库伪装成测试库。正式执行仍需备份、维护窗口及审阅后的操作方式。

| 顺序 | 操作及依赖 | 成功判据 | 失败恢复 |
| --- | --- | --- | --- |
| 1 | 固定代码版本、数据库结构快照/备份；核实服务/测试账号/时区；三个第四阶段开关均0 | 明确目标库、备份可恢复；不依赖测试用户名猜测 | 不启动新链路，保留原系统 |
| 2 | 先资源质量迁移 `20260924_resource_quality`，复用既有字段、建立来源/身份/迁移追踪；已存在数据先预览 | 预览匹配实际列/表，幂等；未核实字段保持未知 | 使用 resource_quality rollback-preview 后仅回滚本版拥有的变更，不删资源/收藏 |
| 3 | 原 user_behavior_events 存在后应用反馈迁移；不修改233历史事件 | migration gate active，偏好与request幂等表存在；无历史数据删除 | 先关反馈/重排/曝光开关，feedback rollback 仅关闭门禁、保留状态和审计 |
| 4 | 资源和关联表稳定后生成搜索迁移预览，再应用触发器、同步状态及原 outbox | 业务事务回滚同时撤销版本/事件；所有已支持写入口触发器存在 | 先停worker；用匹配rollback预览移除本版触发器，队列/审计保留 |
| 5 | 初始化独立新索引→临时索引重建→核对文档/设置→原子切换 | reconcile missing/stale/not_public_or_removed均空；任务最终succeeded；revision一致 | 构建失败保留在线索引。先切 SEARCH_BACKEND=database并重启读取进程，再recover/retry/rebuild；不盲目重复swap |
| 6 | 启动单独 worker，确认任务成功后推进 indexed_revision；Redis用独立命名空间 | outbox收敛、dead=0；数据库与索引版本一致，冷热搜索结果一致 | 保留pending/dead/last_error；status确认后人工retry；超时栅栏先recover。业务保存成功不改报失败 |
| 7 | 开普通搜索、AI规则及相似资源，反馈/重排/visible-v2仍0 | 名称/标签/用途、分页分类、零结果不降级；故障降级有元信息 | SEARCH_BACKEND=database，保留API响应；Redis故障无缓存运行 |
| 8 | 凭据到位才做模型小规模联调；另在隔离环境依次开反馈/新版曝光/重排 | 当前条件与证据/账号归属/未知/异常验收通过；重排保留原分数 | AI_REQUIREMENTS_MODEL_ENABLED=0回规则；三个阶段4开关归0并重启，再核对baseline证据 |
| 9 | 另行审阅29个获批待新增关联，16未决继续隔离 | 当时库上重新预览，批准子集与资源身份一致；重复与回滚已隔离验证 | 按版本拥有关系回滚，只撤销本次新增关联；不动既有标签 |

缓存失效顺序：业务事务同时递增数据库revision并写outbox；未追平时不使用旧索引缓存，读取当前公开状态；确认Meili任务成功后更新indexed_revision，形成新缓存键。键包含查询/筛选/排序/分页及数据版本。返回前再核当前资源状态，防止下架延迟泄漏。

### 可重现命令（仅隔离环境）

在仓库根目录，先查看上面 JSON 中的实际库名；不要直接用业务库配置：

```powershell
# 只读业务证据与批准子集预览
python backend/scripts/audit_behavior_readiness.py --output docs/release/current-readiness-audit-final.json
python backend/scripts/resource_quality.py tags-preview --input docs/recommendation/v3-tag-identity-20260925/resolved-review.json --source-review docs/recommendation/v3-tag-review-queue.json --migration-version 20260925_v3_tag_identity_v1 --output docs/release/tags-current-preview.json

# Docker恢复后，仅启动本次已有的两个隔离容器；不得 docker compose down 用户栈
docker start zhihangyu-local-integration-meili zhihangyu-local-integration-redis
# 准备脚本仅接受resource-chain.json中指定的本机库，含迁移与重建；重复前审阅测试数据变化
python backend/scripts/local_integration.py prepare --database resource_chain_7a54fb93b0d4_test
python backend/scripts/local_integration.py worker --database resource_chain_7a54fb93b0d4_test
# 各自独立终端；默认三个新开关为0
python backend/scripts/local_integration.py serve --database resource_chain_7a54fb93b0d4_test
$env:API_PROXY_TARGET='http://127.0.0.1:15000'
npm run dev --prefix backend/frontend -- --host 127.0.0.1 --port 15173 --strictPort
# 停止上述测试serve进程后，才允许测试开启（不能同时监听15000）
python backend/scripts/local_integration.py serve --database resource_chain_7a54fb93b0d4_test --new-policy
# 可选慢反馈故障注入：追加 --feedback-delay-seconds 30，其他接口无延迟
python backend/scripts/audit_local_integration_events.py
```

搜索维护CLI需要环境 `SEARCH_TEST_DATABASE_URL`（本机上述测试库DSN，凭据不入库/日志）、`SEARCH_TEST_INDEX=stage2_test_release_resource_chain_7a54fb93b0d4_test`、`MEILI_HOST=http://127.0.0.1:17700`、`REDIS_URL=redis://127.0.0.1:16379/7`。依次：

```powershell
python backend/scripts/search_sync.py migration-preview --test-database --output artifacts/local-integration/migration.json
python backend/scripts/search_sync.py migration-apply --test-database --preview artifacts/local-integration/migration.json
python backend/scripts/search_sync.py reconcile --test-database
python backend/scripts/search_sync.py status --test-database
python backend/scripts/search_sync.py recover --test-database
python backend/scripts/search_sync.py retry --test-database
python backend/scripts/search_sync.py rebuild --test-database
python backend/scripts/search_sync.py once --test-database
python backend/scripts/search_sync.py migration-rollback-preview --test-database --output artifacts/local-integration/search-rollback.json
# 先停worker/读取降级，并审阅预览，才执行：
python backend/scripts/search_sync.py migration-rollback --test-database --preview artifacts/local-integration/search-rollback.json
```

`recover`用于不确定提交/超时后的任务栅栏恢复，不需要每次启动执行。重建保留旧索引，但旧索引不代表包含最新增量；优先数据库回退+重建，不直接交换旧索引当作完全恢复。

Compose正式准备命令为 `docker compose --profile search-sync up -d search-worker`，前提是独立完成迁移及索引初始化。`start.bat` 不自动启用 profile，`status.bat` 查看当前容器，更新后的 `stop.bat` 覆盖worker且不删volume。此处命令是启用清单，本轮未对正式栈执行。

## 真实模型、环境阻碍与人工事项

现有进程环境或 `backend/.env` 中 `DEEPSEEK_API_KEY` 不存在，仅报告有无。[real-model.json](real-model.json)为 `not_executed / missing_credentials`，模型调用0。现有 `AI_REQUIREMENTS_MODEL_ENABLED` 默认1；缺凭据/超时/无效输出回规则与公共搜索，不影响普通搜索。授权配置后运行：

```powershell
python backend/scripts/verify_stage3_real_model.py --run --database ai_retrieval_80183efd0298_test --output docs/release/real-model.json
```

不要求在聊天中发密钥。命令复用既有客户端，最多10次真实调用、五组隔离案例，失败不伪装成规则通过。

9月28日上午历史错误（已恢复，不作为当前阻碍）：`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`。此前 Docker host 日志显示 Inference manager 无法移除 `%LOCALAPPDATA%\Docker\run\dockerInference`，`The file cannot be accessed by the system`，listener 路径语法错误。不是项目端口占用或浏览器缺失。没有删除Docker文件、重置WSL、清空卷或反复重试同一启动。

若日后同类错误复发的人工步骤（本次无需执行）：从托盘退出Docker Desktop，重新打开等待Engine就绪；若仍出现同一锁定路径错误，重启Windows后再启动Docker，提供脱敏诊断或修复安装。以 `docker info` 成功为准，再启动上述两个具名测试容器；不要删除数据卷。上述全链路现已补齐，见本报告首节与 sync-recovery.json。

还需：确认业务数据源及测试账号完整名单；16条具体身份清单见阶段1 manual-checklist；29条迁移预览本轮重新核对仍29待新增/1已有。初次调度延迟问题已由隔离后端响应栅栏解决，确定顺序的真实浏览器换号证据见首节。后台亚秒阈值竞争、完整动画/所有遮挡、相似页浏览器交互仍需补验。

结论：代码修复和隔离验证具备继续准备的条件；公共搜索、同步、缓存已有服务级证据，常规问卷/搜索/收藏/反馈已有真实浏览器证据。**正式迁移、模型、反馈/新版曝光/重排推广仍不能据此自动开启**。业务数据仍“无法评估行为实验条件”，不开展算法实验。

## 结束状态与清理

本轮结束已按完整命令行核对并停止独立 Chrome（19223）、Vite（15173）、隔离 Flask（15000），检查三个端口均无监听。没有停止用户已有 MySQL；实际配置文件未改变，第四阶段默认关闭。慢请求注入随隔离进程停止而结束，不保留运行中的新策略。

测试库、JSON和截图保留以便审阅，不批量删除。9月29日收尾已停止 `zhihangyu-local-integration-meili`、`zhihangyu-local-integration-redis`，容器及测试数据保留；共享Docker Desktop与用户MySQL未停止。本轮未挂载用户已有数据卷，也未运行 prune 或删除卷。
