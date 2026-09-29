# 第三阶段：结构化需求与相似资源

2026-09-25。已实际修改代码并完成下列本地验证；没有推送、部署或修改正式数据库，没有进入第四阶段。**真实模型联调未执行（缺少凭据），不能称为真实模型验收通过。**第三阶段收尾已解决两份前端检查的 5 项契约差异，并修复全局助手的账户切换及迟到响应问题；详见文末收尾记录。

## 承接状态与变更边界

读取了第二阶段报告及验证 JSON、第一阶段报告、Git 状态和实际代码。实际工作目录为 `D:\study\智汇\wwww_git`，正式前端在 `backend/frontend`，后端入口为 `backend/app.py` / `backend/wsgi.py`。未发现适用 AGENTS.md。已有大量未提交修改全部保留，没有重置或恢复无关文件。

第二阶段仍未正式启用，本阶段只在新建隔离数据库安装其搜索迁移；没有对正式库安装触发器或启动正式同步 worker。第一阶段 16 条身份未决记录继续隔离，没有读取候选映射作为已确认身份。再次运行只读标签预览，结果仍为 **29 个待新增关联、1 个已有关联**，见 [本次预览](stage3-tags-still-pending.json)。没有修改冻结推荐权重。

## 修改文件与调用流程

| 文件 | 本阶段修改 |
| --- | --- |
| `backend/ai_requirements.py` | 规则解析、原文依据、结构化模型输出验证、矛盾及未知限制澄清 |
| `backend/ai_model_client.py` | 复用原 DeepSeek 配置及端点的有界 JSON 客户端；超时/无效响应安全分类 |
| `backend/ai_retrieval.py` | 统一候选检索、条件核对、排序、证据理由、模型说明校验和相似资源评分 |
| `backend/search_catalog.py` | 复用第一阶段字段 claims 投影和数据库中已确认的 active 身份关联；不读取待审文件 |
| `backend/search_service.py` | 可选 AI 候选上限及截断元信息；普通搜索默认行为不变，缓存键包含候选上限 |
| `backend/v1_routes.py` | 实际应用注入公共搜索服务后接入结构化 AI；详情及 similar 接口复用相似度服务 |
| `backend/ai_server.py` | 旧独立入口也从真实公共资源组装 title/url/snippet，移除让模型生成网站链接的旧链路 |
| `backend/.env.example` | 增加可选 `AI_REQUIREMENTS_MODEL_ENABLED` 开关，复用 `DEEPSEEK_API_KEY` |
| `backend/frontend/src/components/ai/AiSiteAssistant.vue` | 沿用现有组件和 CSS，补充需求、匹配等级、未知/不满足条件、澄清及降级状态 |
| `backend/frontend/src/components/site/SiteList.vue`、`src/views/SiteDetail.vue` | 沿用 SiteCard 理由展示，相似资源列表启用理由；其他列表默认不变 |
| `tests/test_ai_retrieval_stage3.py`、`tests/test_ai_model_transport_stage3.py` | 规则、模拟模型、约束核对、候选范围、下架及相似资源测试 |
| `backend/scripts/verify_ai_retrieval_stage3.py`、`verify_stage3_regressions.py` | 可复现隔离链路和相关回归，单独保存第三阶段报告 |
| 前端 `scripts/verify-ai-structured-results.mjs`、`verify-ai-error-contract.mjs` | 实际组件提交函数回放；原错误契约断言未改，只注入新增响应状态依赖 |

实际主链路：AiSiteAssistant → 现有 axios/JWT → `POST /api/ai/site-recommend` → 规则与可选模型解析 → 第二阶段 `SearchService.retrieve` → 逐项事实校验 → 当前需求排序、画像仅作末级补充 → 可选模型选择证据 → 再读公共 Catalog 校验当前状态及事实 → 服务端组装真实 ID/名称/链接 → 兼容成功响应。

未注入 SearchService 的旧 `register_v1_routes` 测试/嵌入式调用保留兼容分支；正常 app 注入服务。七字段错误响应及 HTTP 状态不变。成功响应保留旧字段，新增 `requirements/clarifications/degraded/notice/coverage`；每条结果新增 `match_status/condition_checks/unmet_conditions/unknown_conditions/match_evidence`。

## 条件和未知值规则

每项条件有 `field/value/strength/evidence/label`，保留 `original_query`；`evidence` 必须是本次查询原文。字段包括用途、场景、收费、语言、平台、安装、门槛、排除项，以及复用的登录要求。

- 明确条件默认为必须，最好/优先/尽量等为偏好；不限、允许安装表示放宽，不制造新限制。场景陈述作为排序偏好。
- 收费区分 `free/freemium/trial/paid/any`，免费试用和部分免费不能满足完全免费。旧 `is_free` 布尔值不能证明完全免费。
- 语言为受支持语言列表；平台和门槛复用 `entry_requirements` 结构，支持安装 `none/required`。非法类型、无法识别枚举和缺失字段是未知。存在 claim 但缺少 `verified_at` 时，该收费/语言/门槛等条件也为未知。已存储的合法结构化列仍兼容读取，不据旧描述猜收费。
- `不要付费` → 完全免费；`不需要中文也可以` → 语言不限。未可靠理解的否定或必须限制提示澄清；不把“翻译英文资料”直接当成界面必须英文。
- 收费等必选条件相互冲突时先澄清，不检索、不擅选。过多条件或没有明确用途也要求补充。
- 模型输出必须恰好匹配 schema、枚举和原文，不能删除或强化规则识别的条件。新用途只能是查询中的逐字引用；新硬限制没有规则支持就回退。此保守策略会降低复杂自然语言的模型接受率，真实模型可用率尚未验证。
- 本次需求先于画像；职业及兴趣只在匹配等级、当前任务/必选/偏好评分之后补充排序，画像不会添加收费等硬条件，也不会送给模型。

匹配等级：所有必选条件经实际字段验证才为 `full`（完全符合）；有必选条件明确不符为 `partial`；没有已知不符但仍有未知必选条件为 `unverified`。偏好不满足不取消完全符合，仍逐项显示。排除产品命中的结果直接移除。不相关资源不凑数。

先以用途及受控同义词走公共搜索服务；候选少于 100 时，经同一个服务扩展公共目录。最多评估 5,000 条，额外探测截断；截断时明确提示不能推断全库无结果。`coverage` 标记 matched_candidates/public_catalog、检索数、评估数及截断状态。无完全符合结果只陈述“本次检索范围内”，不声称全库没有。

## 理由和身份依据

用途证据来自当前 `name/tags/use_cases/summary/description` 的实际匹配片段；场景来自 `occupations/audience/use_cases`；收费、语言、使用门槛来自合法结构化字段，随理由数据保留字段名、来源引用和核验时间（缺失不补造）。第一阶段既有投影继续人工优先、排除 AI 建议。

模型说明只能选择已存在候选 ID 下的已满足证据编号，不能生成自由事实、名称或 URL。全部候选和证据通过校验后才采用；任一伪造 ID、链接、额外字段或无效证据使说明退回确定性模板，已有真实检索结果保留。模板使用“资源标签/摘要包含某用途”等克制表述。网页全文不传给模型、不执行其中指令；前端用 Vue 文本插值，无 `v-html`。

模型说明结束后再次读取当前公共快照，删除已下架资源，并重新核对条件及理由。身份去重只使用数据库 `resource_identity_links` 中已确认 active 关系，或相似资源中的完整规范化 URL；不按同域名/同名合并，不处理第一阶段未决记录。

## 相似资源排序

`GET /api/sites/<id>/similar` 及详情中的 `similar_sites` 共用统一资源投影。至少存在一个有效共同标签或用途匹配才进入结果；仅同分类不够。过滤“工具/网站/免费/中文/ai”等弱标签。

评分：每个共同有效标签 6 分，每个共同用途 8 分，同分类 2 分；收费、语言、安装、门槛和平台每项已知相同条件加 1 分。按分数降序、ID 升序稳定排序。排除自己、已确认同产品、完整 URL 重复和下架资源；同域名不同产品保留。收费不同仍可推荐，但说明双方收费模式；未知收费标记待核实。没有可靠相似项时可为空。

## 配置、超时和降级

复用 `DEEPSEEK_API_KEY`、`deepseek-chat` 和现有 DeepSeek 端点；无需新模型账户或向量服务。`AI_REQUIREMENTS_MODEL_ENABLED=0` 或缺少 key 时直接采用规则解析及真实检索，不影响普通搜索。没有新增正式数据库迁移。

输入限制 500 字、最多 20 项条件、每项字符串最多 120 字；模型请求 JSON 最多 12,000 字，响应最多 65,536 字节，内容最多 12,000 字，最多 1,200 输出 token。每次用户请求最多两次模型调用（解析、证据选择），不自动重试；单次读超时不超过 8 秒，连接不超过 2 秒，共享 12 秒剩余预算并在分块读取时检查。同步 HTTP 的连接/阻塞读取可能使总墙钟时间略超预算，这不是硬实时截止保证。

超时、不可用、非法 JSON/schema 均回退规则；未可靠解析的限制保留澄清，不能宣称已满足。说明校验失败只回退模板。日志仅记录耗时、候选数、截断及分类降级原因，不输出密钥、模型响应或私人画像。公共搜索继续区分正常零结果与 Meili 故障，Redis 故障允许无缓存运行。

运维回退可关闭可选模型，继续规则和全文/标签检索；搜索故障按第二阶段既定数据库降级处理。不要为回退本阶段重置整个工作区或运行标签迁移。正式启动/停止仍沿用现有 `start.bat/stop.bat/status.bat`；第二阶段正式索引启用仍须完成其既定迁移审阅，本阶段未代为执行。

## 第三阶段首轮验证与复现（历史记录）

Windows 本机 Python 3.14.5、MySQL 9.7.1；隔离 Docker Meilisearch 1.12.8（17700）、Redis 7.4.11（16379）。最终链路运行使用新库 **`ai_retrieval_80183efd0298_test`**、新索引 `stage3_test_80183efd0298`，8 条固定虚构资源和隔离用户，没有复制真实用户数据。模型全部为固定 double，没有真实供应商请求。

| 验证 | 实际结果 |
| --- | --- |
| AI 既有接口测试 | 20 个通过，保留六种无效输入及七字段错误契约 |
| 普通搜索 / 鉴权 / 收藏 / 职业推荐回归 | 分别 11 / 33 / 27 / 9 个通过 |
| 第三阶段需求、筛选、模型伪造、相似度单测 | 23 个通过，含 5,000 候选截断、空/部分结果、模型处理中下架 |
| 模型传输及未核验 claim 测试 | 5 个通过，含请求前限制、超时脱敏、无 key、无效 JSON、超长响应 |
| 合计后端回归 | **128 个通过**；[逐项统计](stage3-regression-results.json) |
| 真实 MySQL + Meili + Redis + Flask 链路 | **36 项检查通过**；[请求、证据和计时](stage3-isolated-verification.json) |
| 前端错误响应回放 | 11 种实际响应通过；未删除或放宽原错误断言 |
| 前端结构化响应回放 | 8 次隔离 API 响应通过，执行组件真实 submit 函数，校验澄清、加载结束、条件、结果和降级状态 |
| 职业切换前端数据流 | 59 项检查通过 |
| 前端 Vite 构建 | `npm run build` 成功，2651 模块；未部署产物 |
| 语法/格式 | 修改的后端模块 `py_compile` 成功；`git diff --check` 无错误，存在仓库 CRLF 转换提示 |

隔离链路覆盖论文绘图（免费、中文、无需安装、新手）、接口调试、否定/矛盾、职业冲突、免费试用/未知字段、模型超时/非法结构/伪造链接、下架和已确认别名、普通搜索故障降级、正常零结果不降级、Redis 不可用仍检索。新索引首个请求为冷缓存 2163.665 ms；后续 7 次请求为 44.659–87.465 ms，其中有重复查询、澄清及状态变更，不能视为统一暖缓存基准。耗时包含本地 Flask/数据库/搜索，**不包含真实模型网络延迟，也不是生产性能**。

复现（仓库根目录；容器须为本项目既有隔离测试容器）：

```powershell
docker start zhihangyu-stage2-meili-test zhihangyu-stage2-redis-test
python backend/scripts/verify_stage3_regressions.py
python backend/scripts/verify_ai_retrieval_stage3.py --create-isolated-test-db
python backend/scripts/resource_quality.py tags-preview --input docs/recommendation/v3-tag-identity-20260925/resolved-review.json --output docs/recommendation/stage3-tags-still-pending.json
Set-Location backend/frontend
node scripts/verify-ai-error-contract.mjs
node scripts/verify-ai-structured-results.mjs
node scripts/verify-career-switching.mjs
npm run build
docker stop zhihangyu-stage2-meili-test zhihangyu-stage2-redis-test
```

测试脚本只接受本机数据库配置，每次创建 `ai_retrieval_<随机值>_test` 及专属索引；不会清空已有库或删真实记录。隔离库和索引保留供复查。本次结束停止上述两个测试容器，不影响业务容器。

## 第三阶段收尾：5 项契约差异已解决

2026-09-25 收尾。重新核对 Git 状态、报告、组件、共享 axios 及后端七字段响应。保留全部已有未提交修改；未修改布局、CSS、动画、模型排序、后端响应契约或数据库数据。

| 差异 | 原检查保护的业务行为 | 当前实际实现及分类 | 修改依据与验证 |
| --- | --- | --- | --- |
| 禁止组件出现 `getAccessToken` | 组件不自行管理凭据、拼接 Authorization 或绕过统一 API | 组件只用现有 auth 工具判断登录；请求走 `aiAPI.recommendSites` 和共享 axios。属于把“不得自建认证”误写为“任何 token 工具调用都不允许” | 保留禁止 localStorage/Authorization/Bearer 及自建 fetch/axios；限定 token 读取只用于共享有效性校验。执行未登录提交，验证请求次数为 0、只跳登录。共享请求契约单独回归 |
| 要求 Home 用登录 `v-if` 挂载并复用 visitSite | 访客不能进入推荐业务，访问网站走统一记录/跳转 | 当前 App 全局单实例，访客按钮保留可见但点击跳登录。这是旧挂载位置检查；同时发现实际缺陷：非首页账户退出/切换没有全局清理，请求可能回填旧账户结果 | 不搬动组件。新增全局账户状态监听、提交前登录门禁、请求代次校验。测试访客无请求、已登录打开、退出清空、迟到结果丢弃；执行 App 的真实访问处理函数，确认真实资源交给统一 siteVisit，缺 URL 走详情 |
| 要求精确 `class="ai-login-prompt"` | 登录提示与 AI 入口不能丢失 | 当前同一元素还有布局/动画 class，提示文案与点击处理仍在。属于源码结构依赖 | 检查完整 class token、登录提示和绑定处理，不要求整个 class 属性只有一个值；原入口、已登录/未登录提示断言均保留 |
| 要求 Home 恰好挂载一次 | 单实例、无重复面板/重复请求，身份失效时关闭 | 实例已迁至 App，Home/Header 为共享入口。属于旧组件位置依赖，并受到上一项实际账户缺陷影响 | 跨 App/Home/Header 断言恰好一个实例并绑定统一跳转；验证账号切换后，旧请求完成不能清掉新请求 loading，也不能替换新结果；保留原 Home 身份关闭检查并增加全局账户监听检查 |
| 要求旧按钮文案“知航AI帮我找网站” | 浮动入口可识别、可触发共享面板 | 当前显示 `AI / 助手`，有 `aria-label="打开知航AI助手"`，使用 handleLauncher。属于旧精确文案依赖 | 检查可访问名称、按钮与点击绑定，执行真实 handler：已登录切换共享面板，访客跳登录且不能发请求；不添加旧文案或无用代码 |

两份脚本原有的 17 / 20 项保护目标均保留；结构相关断言改为等价业务验证，其余键盘、加载、错误、可访问性、API、UI-only store 等断言未删减。新增 `scripts/ai-business-contract.mjs` 共用实际事件处理函数测试；新增 `verify-ai-visible-results.mjs` 编译实际 Vue 模板，验证最终输出的文字与条件分支，不用模拟模板替代当前组件。

### 实际实现修复

`AiSiteAssistant.vue` 监听全局 `loggedIn` 与账户身份变化，关闭面板、清空查询、结果、理解条件和错误，并增加请求代次。提交前未登录直接跳登录；成功、异常、finally 均校验请求代次，防止旧账户响应覆盖新账户或影响新请求加载状态。该保护不依赖 Home 挂载，也不改变正常布局及动画。

原 `verify-ai-error-contract.mjs` / `verify-ai-structured-results.mjs` 只补注入新登录状态与代次依赖，原断言保留。模板渲染另验证旧版数组、旧版 `{items}` 成功响应仍能展示。

相关认证回归额外发现两个旧环境检查问题：强制读取不存在的 `.env.development`、只接受写死的 Vite proxy 文本。现改为读取 Vite 的有效配置及 `resolveApiBaseURL`，仍断言 `/api`；执行实际 Vite 配置，验证默认 `http://127.0.0.1:5000`、changeOrigin 以及既有 Docker `API_PROXY_TARGET` 覆盖。未创建环境文件，也未放宽登录/注册 HTTP 错误和超时断言。

### 收尾实际验证

本轮没有启动任何服务，也没有停止用户服务；无需重建测试库或再次跑首轮 36 项数据库检查。使用已有隔离响应作为前端回放数据，不把历史检查算成本轮新结果。

| 本轮命令/范围 | 结果 |
| --- | --- |
| `verify-ai-site-assistant-panel.mjs` / `verify-ai-unified-entry.mjs` | 17 / 20 项全部通过，内含真实 handler 的登录、全局单实例、账户退出与乱序响应验证 |
| `verify-ai-visible-results.mjs` | 11 个实际 Vue 模板渲染场景通过：条件、未知、部分匹配、空结果、澄清、降级、收藏资源参数、旧数组及旧对象成功响应 |
| `verify-ai-error-contract.mjs` | 11 个回放通过，含六类 HTTP 400、500、401、422 与成功/空结果；七字段错误契约未改 |
| `verify-ai-structured-results.mjs` | 8 个历史隔离 API 响应回放通过，执行当前提交函数 |
| `verify-favorite-star-interaction.mjs` | 24 项通过，覆盖收藏控件、阻止冒泡、按资源 pending、数字 ID/URL 两类接口及后台引用解析 |
| `verify-auth-request-contract.mjs` | 通过，包含有效 API 基址、代理配置、统一请求与现有登录错误处理 |
| 后端相关回归 | **121 项通过**：AI 20、普通搜索 11、鉴权 33、收藏 27、结构化/模拟模型 23、传输/核验字段 5、真实联调命令门禁 2；见 [本轮逐项统计](stage3-closeout-regressions.json) |
| `npm run build` | 成功，Vite 8.2.0，2651 模块，未部署 |
| `py_compile` / `git diff --check` | 成功 |

模型命令门禁测试验证缺凭据、未指定执行、开关关闭时既不连接数据库也不调用模型、不输出测试密钥，且拒绝业务库名。测试初次受 Windows 临时目录权限影响，已改为工作区独立临时文件并通过；本次工作区失败临时目录已清理。未因此放宽功能断言。

模板测试为 Vue 服务端渲染；图标和收藏子组件使用替身，收藏本体另跑上述 24 项检查。网站访问执行当前 App 处理函数，但没有真实打开外部网站。**没有浏览器视觉/真实鼠标交互验收**，不将这些结果描述为浏览器端到端测试。

### 真实模型联调准备及状态

新增 `backend/scripts/verify_stage3_real_model.py`。它复用 `ai_retrieval.configured_model` → 现有 `ai_model_client`，没有第二套客户端、密钥或模型配置。只接收 `ai_retrieval_<12位十六进制>_test` 的已有本机隔离库，并验证 8 条指定虚构资源；公共 SearchService 使用明确数据库模式和只读 Catalog，无正式库读写、无索引/队列变更。测试模型是真实 DeepSeek，候选来自真实隔离数据库记录；不使用真实用户画像或声称虚构资源是已核实网站。

固定五个用例：多条件论文绘图、不要付费且中文不限、免费/必须付费矛盾、论文绘图与程序员画像冲突、资源收费/语言/安装未知。每个最多两次模型调用，合计最多 10 次。检查模型解析确实被接受、原文依据、条件及匹配状态、当前需求优先、未知不算符合、矛盾先澄清、ID/名称/链接来自已有候选；说明或解析降级会判本次真实联调失败，不能用规则成功掩盖真实模型失败。失败报告只保留异常类别，不输出供应商原始响应或密钥。

凭据来自进程环境变量或现有 `backend/.env`（`load_dotenv(..., override=False)`，环境变量优先），不要提交文件，也无需在聊天中提供密钥。

- `DEEPSEEK_API_KEY`：现有供应商凭据。
- `AI_REQUIREMENTS_MODEL_ENABLED`：默认 `1`；设为 `0` 时应用使用确定性规则，命令记录未执行。
- 模型名称、端点、调用预算沿用本报告前面的现有客户端配置；本次未新增配置体系。
- 缺 key 时应用仍进行规则解析及公共检索，未知限制澄清、未知事实不标完全符合。模型超时/无效输出同样回退并提示。普通搜索没有模型依赖，相关回归已通过。

在已通过本地安全方式配置凭据后，从仓库根目录手动运行：

```powershell
python backend/scripts/verify_stage3_real_model.py --run --database ai_retrieval_80183efd0298_test
```

该库来自首轮隔离验证；命令无需启动 Meili/Redis。若本地测试库已移除，可按上文隔离链路脚本生成新库，再使用其报告的库名；只启动未运行的自有测试服务，结束只停止本次启动的服务。不要用业务库代替测试库。

本次实际运行上述真实联调命令：**真实联调未执行**，原因 `missing_credentials`，`real_model_executed=false`，实际模型调用 **0 次**，见 [联调状态](stage3-real-model-verification.json)。没有用模拟输出填充五个真实用例。模拟测试已单独通过，未反复执行模拟测试替代真实联调。

### 遗留与第四阶段条件

第三阶段可执行收尾已完成，5 项差异已解决。**具备进入第四阶段本地开发的条件**，但本次不进入第四阶段，也不等于具备发布验收条件。真实模型结构接受率、自然语言准确率及供应商网络延迟仍需凭据后联调；这是外部依赖。浏览器视觉和真实点击仍未验收，现有自动验证范围已如实列出。

第一阶段 16 条身份未决、29 个待新增关联仍未生效；本轮无数据库写入、无标签迁移。第二阶段仍未正式启用。上述事项不因本轮检查通过而被自动批准。没有推送、部署或操作生产数据库。
