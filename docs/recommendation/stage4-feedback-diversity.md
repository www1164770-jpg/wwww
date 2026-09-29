# 第四阶段：反馈与多样性

更新：2026-09-27。代码及可执行的本地验证已完成；默认仍使用原推荐策略。浏览器真实点击与视觉验收未完成，不作为正式启用依据。本次不进入第五阶段。

## 范围与文件

承接前三阶段实现，保留工作区原有修改。冻结的 `recommend_service.py` 匹配权重未改动，不启用行为权重融合或协同过滤。

- `backend/recommendation_stage4.py`：独立重排、有效偏好、幂等事务与审计。
- `backend/recommendation_feedback_routes.py`：登录用户偏好 API，以及公共资源校验后的推荐装饰器。
- `backend/v1_routes.py`：职业与普通主动推荐接入、曝光版本与去重、指标分版本筛选。
- `backend/scripts/feedback_migration.py`：版本化迁移、预览及非破坏性回滚。
- `backend/scripts/stage4_fixtures.py`、`evaluate_stage4.py`、`verify_stage4_feedback.py`、`tests/test_recommendation_stage4.py`：固定样本、离线对比及隔离验证。
- 正式前端位于 `backend/frontend`。新增 `src/stores/recommendationPreferences.js`、`components/site/RecommendationFeedback.vue`、`RecommendationPreferencePanel.vue` 和 `utils/recommendationPages.js`、`visibilityWindow.js`、`recommendationVisibility.js`。
- 接入现有 `Home.vue`、`SiteCard.vue`、`App.vue`、`PersonalizationView.vue`、`behaviorTracker.js`、`admin/RecommendationMetrics.vue`；沿用卡片、设置页和通知样式，不改页面主布局与动画。

调用流程：现有画像与冻结排序 → 当前公共资源状态/已确认身份 → 当前用户有效偏好 → 可选重排 → 原响应附加版本和位置字段 → 首页卡片。搜索、AI 主动查询、详情、收藏不接入负反馈过滤。

## 策略与回退

基线算法 `phase1-v1`；重排策略 `diversity-v1.b5`（后缀记录分数带宽）。保持 `match_score` 和原理由不变，另附 `baseline_position`、`rerank_position`、`rerank_reason`、`rerank_version`。

只处理已审核、启用、有任务/方向/标签相关证据的候选；排除不满足或未知的必选条件。先按已落库确认的 `canonical_site_id` 去重，再在连续、与首项分数距离不超过带宽的候选组中增加标签、类别、来源覆盖。同域名仅作为来源多样性信号，不作为产品身份；同名、重复描述也不作为身份依据。未知标签/类别/来源不补造。当前类别作为工具类型代理，尚未增加新分类体系。

排序稳定；不足时返回少量结果，不循环补位。普通主动推荐启用新策略时获取最多 200 个候选再截断；职业链路保留现有有界候选池，不宣称全库穷尽。首页新策略池按每页 1–16 条有限切片，最后一批不从首批补足，到末批禁用“换一批”。固定池与固定页大小不重复、不漏项；职业、偏好或响应式页大小改变后属于新的批次划分。

以下配置在 `backend/.env.example` 中均有说明；本次没有更改实际环境开关：

| 配置 | 默认值 | 作用 |
| --- | --- | --- |
| `RECOMMENDATION_RERANK_ENABLED` | `0` | 独立多样性策略 |
| `RECOMMENDATION_DIVERSITY_BAND` | `5` | 近似相关分数范围，允许 0–10 |
| `RECOMMENDATION_FEEDBACK_ENABLED` | `0` | 用户偏好 API 与主动推荐过滤 |
| `RECOMMENDATION_EXPOSURE_V2` | `0` | 新可见曝光口径 |
| `RECOMMENDATION_KNOWN_DAYS` | `7` | 已知资源后置期限 |
| `RECOMMENDATION_LATER_DAYS` | `30` | 暂不需要暂停期限 |

仅在完成迁移、使用隔离数据库并接入第二阶段公共 catalog 的进程中开启验证；无 catalog 时明确失败，不悄悄跳过当前资源校验。全部开关关闭时直接返回原候选对象，不查询偏好表。回退时先关闭开关并重启对应进程，再按需要停用迁移门禁；不回滚其他阶段代码。

## 负反馈与账号安全

`GET/POST /api/recommendation/preferences` 复用 JWT 身份与七字段响应 helpers。服务端取当前登录用户，拒绝客户端 `user_id`、无效原因、额外字段与不合法版本。未登录不生成保存状态。反馈失败恢复卡片并提示；冲突或不确定网络结果重新核对服务端状态。

| 原因 | 作用 | 恢复 |
| --- | --- | --- |
| 不相关 | 仅排除该用户主动推荐中的该资源 ID；不扩展到标签、职业或待决别名 | 即时撤销或设置页恢复；默认不自动到期 |
| 已经知道 | 默认 7 天内在相关性相近的结果中后置 | 撤销、设置页恢复或到期 |
| 暂时不需要 | 默认 30 天暂停该资源的主动推荐 | 撤销、设置页恢复或到期 |

“已经知道”是后置规则，不是严格曝光频次上限；候选很少时仍可能出现。即时撤销清除当前有效偏好、恢复正常推荐，不还原更早的其他原因。所有反馈均不取消收藏、不降低全站质量分、不阻止访问。

有效状态表和历史事件分开：`recommendation_preferences` 保存原因、修订号、期限；`recommendation_feedback_operations` 保存请求幂等回执；现有 `user_behavior_events` 保存 `feedback` / `feedback_undo` 独立事件。用户行和偏好行加锁，修订号进行并发比较，状态、审计、回执同事务。重复相同原因不续期、不重复审计；同请求 ID 不同内容返回冲突。撤销保留历史。

实测修复了 MySQL REPEATABLE READ 下并发旧快照问题：等待用户锁之后对回执/偏好及曝光去重使用锁定当前读。陈旧撤销返回 409，不覆盖较新操作。

前端按账号代际、请求序号与偏好修订号丢弃旧响应；退出/换号清空状态。仅显式 `activeRecommendation` 卡片执行隐藏和菜单逻辑，收藏、搜索和详情即使带有旧推荐元信息也不受影响。反馈后清理当前账号职业池并重新获取；第四阶段推荐池不持久化到职业缓存，防止过期偏好或策略快照重新回填。基线缓存逻辑保留。到期计时刷新当前列表。

## 迁移、预览与回滚

版本：`20260926_feedback_v1`。新增三张表（含版本门禁），复用已有行为表。预览见 `stage4-migration-preview.json`，回滚预览见 `stage4-rollback-preview.json`。

仓库根目录运行，凭据从已有本地配置/环境读取，不写入报告：

```powershell
python backend/scripts/feedback_migration.py preview --output docs/recommendation/stage4-migration-preview.json
python backend/scripts/feedback_migration.py rollback-preview --output docs/recommendation/stage4-rollback-preview.json
python backend/scripts/verify_stage4_feedback.py
python backend/scripts/evaluate_stage4.py
python -m unittest discover -s tests -p test_recommendation_stage4.py
```

隔离验证命令自动新建 `feedback_<12hex>_test` 库；只接受本机数据库，不写源库。现有测试库 `feedback_e0f639b0ace2_test` 可供检查。手动重复执行示例：

```powershell
python backend/scripts/feedback_migration.py apply --database feedback_e0f639b0ace2_test --preview docs/recommendation/stage4-migration-preview.json --output artifacts/stage4-apply.json
python backend/scripts/feedback_migration.py rollback --database feedback_e0f639b0ace2_test --preview docs/recommendation/stage4-rollback-preview.json --output artifacts/stage4-rollback.json
```

执行要求预览内容一致，CLI 拒绝非隔离库名。回滚仅关闭版本门禁，保留有效状态、幂等回执和审计，不删表不删数据；重新 apply 可恢复。MySQL DDL 可能隐式提交，迁移通过幂等建表处理重试，不假设 DDL 原子回滚。尚未提供或执行生产迁移入口。

本阶段未新增工作进程，也未启动或停止任何用户服务。实际验证复用已运行的本机 MySQL，并使用 Flask test client；测试库保留供复核。前端本地构建：进入 `backend/frontend` 执行 `npm run build`。无需修改现有 start/stop 脚本。

## 曝光与看板

- 默认 `legacy-v1` 保持历史口径；开启曝光开关才使用 `visible-v2`。反馈事件独立版本 `feedback-v1`，不混算点击或收藏。
- 新曝光要求卡片与视口交集至少 50%，前台标签页连续可见 1000ms；滚出阈值、切后台、卸载或更换资源均取消计时。接口返回、预加载不计曝光；没有 IntersectionObserver 时不计新曝光。
- 同一用户、标签页 session、批次、资源、事件版本去重；前端还区分重排版本，服务端串行校验避免并发重复。同一批次应保持固定策略版本。换批生成新批次；重复渲染不重复计数。账号变化后旧定时器不能上报到新账号。
- 服务端验证曝光参数与版本，但客户端可见性是上报口径，不是防作弊证明；IntersectionObserver 不证明卡片未被其他浮层遮挡。真实浏览器遮挡情况尚未验收。
- 事件记录资源、批次、算法、重排版本和时间；反馈另记原因与修订号。算法/批次上下文由前端提供并限长，不作为可信身份或权限输入。
- 看板按 `event_version` 筛选，默认 legacy；可进一步按 `rerank_version` 筛选。旧快照表没有事件版本，因此禁止创建 v2 快照，避免混入历史趋势；v2 实时指标可查看。历史数据未改写。

## 离线对比与实际验证

完整结果：`stage4-offline-evaluation.json`、`stage4-isolated-verification.json`、`stage4-regressions.json`。离线使用 12 条明确标记为合成的资源、2 个固定画像，涵盖文献/接口相关、不相关、同产品别名、下架和必选条件失败。预期任务/类型标签独立手工定义，不由排序函数生成；基线调用真实冻结 rank_sites，在相同合法候选上比较前三项。

| 指标 | 文献基线 → 新策略 | 接口基线 → 新策略 |
| --- | --- | --- |
| 前三项任务相关率 | 1 → 1 | 1 → 1 |
| 已确认产品重复率 | 1/3 → 0 | 1/3 → 0 |
| 任务覆盖数 | 2 → 3 | 2 → 3 |
| 工具类型覆盖数 | 2 → 3 | 2 → 3 |
| 必选条件违反数 | 0 → 0 | 0 → 0 |
| 理由字段依据 | 有效 → 有效 | 有效 → 有效 |

20 次进程内热运行顺序一致。基线中位耗时约 0.143/0.171ms，额外重排约 0.021/0.024ms；没有 DB、Redis、网络或模型调用，不是生产性能，也没有测端到端冷缓存。本样本不证明真实用户点击率、满意度或长期多样性改善，尚不支持正式上线。

实际执行：

- 新增后端 10 项测试通过：冻结权重、关闭开关无 DB 访问、公共/相关/必选条件、确认身份去重、同域名独立、分数带、反馈范围/到期/后置及稳定性。
- 隔离 MySQL 24 项检查通过：迁移重复执行、鉴权、跨账号、输入验证、回执幂等、陈旧撤销、并发修订、审计失败事务回滚、到期、可见曝光并发去重、新旧口径分离及非破坏性回滚/恢复。
- 现有后端 108 项回归通过：排序 3、职业 9、观察指标 5、AI 20、普通搜索 11、鉴权 33、收藏 27。末轮针对排序/职业/观察重新执行 17 项，并再次执行新增 10 项，均通过；重复执行不计作新增测试数。
- `verify-stage4-feedback.mjs` 通过：真实 store 的乐观更新、失败恢复、撤销、换号/退出竞态、乱序读取、到期；可见计时阈值/后台/滚动重置；35 条资源在页大小 1/6/16 下完整无重复切片。
- `verify-stage4-card-scope.mjs` 编译实际 SiteCard 模板验证主动推荐隐藏、其他场景保留卡片和收藏按钮；属于 SSR 验证，不是浏览器点击。
- 职业切换 59 项、收藏星标 24 项、AI 七字段响应回放 11 项及指标看板检查通过。最后前端生产构建成功，转换 2659 个模块。

没有删除、跳过或降低既有测试断言；旧版响应结构保留，新增字段附加。

## 浏览器及继承待验事项

浏览器控制实际尝试失败：`cua.getState()` 返回空 apps/browsers，错误为 `Browsers: Error: nodeRepl.fetch request failed`；本地亦未提供 Playwright/Puppeteer 包。未执行任何真实浏览器点击、截图或视觉验收。

仍须在可用浏览器和隔离服务上验收：桌面/窄屏反馈菜单及遮挡、选择原因后卡片更新、网络失败恢复、即时撤销、设置页恢复、收藏与网站跳转、职业切换/换批/分页、退出/换号与慢响应，以及原动画。上述 store/SSR 测试不能替代这些步骤。

真实模型联调仍因缺少凭据未执行，本阶段没有以模拟结果冒充真实调用。第二阶段尚未正式启用；第一阶段 16 条身份未决记录和 29 个待新增标签关联继续未生效。本次没有推送、部署或操作生产数据库。

结论：第四阶段代码、迁移预览和隔离自动化验证可供审阅，默认策略未改变；浏览器验收与真实模型联调仍是外部依赖，不能宣称全部验收通过或自动正式启用。
