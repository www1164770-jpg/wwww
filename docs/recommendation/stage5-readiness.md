# 第五阶段：数据就绪评估与采集修复

日期：2026-09-27。交付状态：**评估完成、采集修复完成（代码与隔离验证）；未实施算法实验。** 不能表述为推荐升级全部完成。正式配置未改、未推送或部署。

## 证据和结论

真实来源访问情况：使用项目现有 `backend/.env` / 环境配置，只读连接本机 `127.0.0.1:3306/nav_site`，未读取或输出密码、邮箱、用户名等个人资料。该库不是本阶段生成的测试库，但其中账号是否为真实用户尚未核实，因此不能把库中账号数称作真实独立用户数。

完整聚合证据：[stage5-readiness-audit.json](stage5-readiness-audit.json)。最终采样时间为 2026-09-27 05:59:16 UTC（北京时间 13:59:16）。数据库 session 时区为 SYSTEM，实测偏移 UTC+480 分钟。审计范围为所有已存事件，233 条，未截断；7/30 天窗口无法计算，原因是 **233 条 created_at 全部为空**。旧事件时间不能从 ID、当前时间或报告日期推算。

结论为 **无法评估真实行为实验条件**，并非“零数据”。有记录可供质量审计，但缺少时间、测试账号核验、历史画像与展示证据。即使保守地把全部记录算作有效，规模也尚未达标，因此不引入行为权重、协同过滤、Gorse 或影子排序实现。

## 已有门槛逐项核对

沿用 `phase-2-observation.md` 的观察门槛，不将其改成上线标准。

| 项目 | 当前证据 | 要求 | 判断 |
| --- | --- | --- | --- |
| 曝光 | 232 条未核实账号记录 | ≥1000 | 即使全部有效仍不足 |
| 点击 | 1 条 | ≥100 | 不足；该条还缺少批次 |
| 收藏事件 | 0 条 | ≥20 | 事件表不足；不等于没有收藏业务记录 |
| 回访事件 | 0 条 | ≥10 | 不足 |
| 负反馈 / 撤销 | 0 / 0 条 | 项目无数量阈值 | 新功能未启用，不能解释为满意度高 |
| 职业覆盖 | 历史值未知 | ≥3 个职业，每主要画像曝光≥50 | 无法评估；不拿当前画像代替历史 |
| 方向/需求组合 | 历史值未知 | ≥5 个组合，每主要画像曝光≥50 | 无法评估 |
| 推荐批次 | 19 个带批次曝光组 | ≥20 个有效批次 | 原始数量已不足；有效性仍待核验 |
| 用户 | 1 个已存在账号，真实性未知 | 批次来自≥2 个用户 | 数量上限不足，真实用户数无法评估 |
| 重复曝光 | 0，原始重复率0% | <2% | 存储键检查满足，不证明实际可见 |
| 明显点击双写 | 可比较时间的重复0；1条时间未知 | 0 | 无法完整验证时间双写规则 |
| 无效资源 ID / 用户引用 | 0 / 0 | 无效资源0 | 当前引用存在；不证明过去可公开或归属正确 |
| 未知事件类型 | 0 | 0 | 满足 |
| 时间及观察周期 | 233条缺时间，无首末事件时间 | 可比较7/30天；现有实现最低7天 | 无法评估，不能将日期过滤后的空集当作真实零事件 |
| 推荐孤立点击 | 1条无同账号/资源/批次/session曝光关联 | 需可追溯 | 未满足 |
| 展示位置 | 233条均缺少 | 需关联实际展示位置与批次 | 未满足 |

测试账号只按 `RECOMMENDATION_METRICS_TEST_USER_IDS` 显式排除，不按姓名、邮箱或 ID 猜测。本地未配置该名单，本次未排除任何账号，也没有声称已完成测试账号核验。19个批次未发现跨账号共用，但历史没有服务端签发的批次归属凭证，不能据此证明无跨账号异常。

## 版本与运行链路

存储事件仅有一个版本分区：`legacy-v1 / phase1-v1 / baseline`，共233条。event_version缺失按现有指标口径归 legacy，rerank缺失归 baseline；采集修复版本全部未知。未发现新旧曝光混存，但旧曝光本身不是严格可见口径。审计始终分版本输出，不把反馈事件混算为点击或收藏。

| 环节 | 已有代码 / 隔离证据 | 当前环境事实 |
| --- | --- | --- |
| 行为采集及观察快照 | 代码存在 | 两张表存在；实际行为表时间列可空且 DEFAULT NULL，与迁移声明不同 |
| 第二阶段索引同步 | 此前隔离验证通过 | `search_sync_state`、`outbox_events` 不存在；本次未运行迁移 |
| 搜索 worker | 独立进程入口存在 | 未观察到本机 Python 进程；Docker Linux engine管道不存在，无法查询运行容器；不能宣称 worker运行中 |
| 搜索配置 | 公共服务已实现 | `SEARCH_BACKEND` 未设置，代码默认 meilisearch；这不证明引擎可用。`SEARCH_SYNC_ENABLED` 未设置，worker入口要求显式1 |
| 第四阶段偏好迁移 | 隔离库验证通过 | 正式来源库无 `recommendation_feedback_migrations` |
| 重排/反馈/可见曝光 | 代码存在 | 本地配置均未设置，默认关闭；不是实际运行服务的环境证明 |
| 身份映射 | 第一阶段预览存在 | `resource_identity_links` 不存在；16条未决、29个待新增标签关联未生效 |

本次没有启动业务服务，不能把当前代码配置或离线检查称为端到端运行验证。未探测或修改未知远端环境。数据库迁移/搜索服务正式启用仍需另行授权和验收。

## 实际修改与依据

1. **时间采集修复**：`backend/v1_routes.py` 的统一事件 INSERT 原先依赖表默认值；本机实际表无默认值，这一写法可产生空时间。现在显式写 `NOW()`，沿用现有数据库时区口径，服务端附加 `collection_version=server-time-v1`。不修改曝光定义，不回填历史，不自动 ALTER 表。历史表为何偏离迁移声明尚无证据，不能归因于某次操作。
2. **只读审计**：新增 `backend/behavior_readiness.py`、`backend/scripts/audit_behavior_readiness.py`。在 READ ONLY 一致性快照事务内读取，结束 rollback；不启动 Flask（避免启动时自动建表），不执行 DDL/DML。连接/表缺失明确返回 cannot_evaluate，不输出零计数冒充成功；拒绝常用测试库命名。最多读取100000行，超限标记 truncated并阻止完整评估，不静默抽样。只保存聚合，不输出原始事件、账号或批次标识。
3. **现有看板补充完整性证据**：沿用 `/api/recommendation/metrics/phase-2-3-readiness`，保留旧 `ready` 和原统计口径，附加 `readiness_version=observation-v1-with-integrity-v1`、`experiment_status`、`integrity`。针对相同版本/用户筛选的全部日期记录检查缺时间，避免被时间筛选隐藏。缺时间、未配置测试名单或混合算法/重排版本不宣称实验可用。旧 ready仍仅代表旧观察阈值；就算满足，也需要人工核实历史画像与可见性。`RecommendationMetrics.vue` 复用现有提示组件展示这一区别及存储/缺时间数，无新看板。
4. **账号去重修复**：`behaviorTracker.js` 原 legacy批量曝光键只有batch/site；现在增加已登录账号ID，避免同一标签页换号继承去重状态。不改变曝光定义，历史键不改写，服务端既有按用户去重仍在。没有可识别账号时不制造已记录状态。
5. **未来可见曝光位置**：`Home.vue` 在第四阶段最终展示切片上添加1起始页内位置，`behaviorTracker.js` 仅在visible-v2附加position及 `position_version=display-position-v1`，后端白名单接收。旧批量曝光没有可靠逐项位置，继续未知；不把排序分数位置或数组推测回填为历史展示位置。该改动不启用visible-v2。

展示位置仍是客户端上下文，不能替代真实可见验收和服务端历史批次凭证。当前指标中的画像聚合可能使用当前画像，不能作为历史画像实验样本；审计明确输出历史覆盖未知。没有为了使门槛通过而将unknown计作真实画像。

无需数据库迁移；没有数据回滚步骤，因为源库没有写入。代码回退仅撤销本阶段写入修复/附加字段和提示，不回滚用户原有修改。新采集版本不影响旧事件读取或七字段响应。

## 复现与验证

仓库根目录，复用已有本地配置，不在命令行传密码：

```powershell
python backend/scripts/audit_behavior_readiness.py --output docs/recommendation/stage5-readiness-audit.json
python -m unittest discover -s tests -p test_behavior_readiness_stage5.py
python -m unittest discover -s tests -p test_recommendation_observation_phase_2_2c.py
node backend/frontend/scripts/verify-stage5-collection.mjs
node backend/frontend/scripts/verify-career-switching.mjs
node backend/frontend/scripts/verify-recommendation-metrics.mjs
npm run build --prefix backend/frontend
```

只有人工核实完整测试账号名单后，才可使用审计参数 `--test-accounts-reviewed`；允许核实后的空名单，但参数本身不证明真实性，也不会自动批准实验。尚未核实不能为了去除告警而传该参数。

实际结果：新增审计6项通过（空时间未知、未核实账号、版本分区、显式排除、孤立点击、只读失败回滚）；已有观察快照/API回归5项通过；新增前端采集函数回放通过（跨账号去重、精确位置、原可见阈值不变）；职业切换59项和现有指标检查通过。最终前端构建成功，2659模块。

真实 MySQL 隔离验证复用 `backend/scripts/verify_stage4_feedback.py` 的 `run(event_timestamp_default=False)`，将测试表构造为与当前库一样没有时间默认值，并新增明确时间/版本断言。25项全部通过，见 [stage5-isolated-verification.json](stage5-isolated-verification.json)，数据库 `feedback_f3c0f6749150_test`。包含真实事件路由写时间、曝光并发去重、鉴权、跨账号、反馈幂等/撤销/到期与迁移回滚。不复制真实用户，不把这些测试事件计入就绪数据。只创建本次隔离库，未启动或停止任何用户已有服务；测试库保留供复核。

可重新执行该隔离验证并保存独立结果：

```powershell
@'
import sys,json
from pathlib import Path
sys.path.insert(0,'backend/scripts')
from verify_stage4_feedback import run
result=run(event_timestamp_default=False)
Path('docs/recommendation/stage5-isolated-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
'@ | python -
```

## 未完成验收及启用条件

本次重新调用浏览器 `cua.getState()`，仍返回空apps/browsers与 `Browsers: Error: nodeRepl.fetch request failed`。未执行真实点击、后台切换或截图，不能用函数回放替代。仍待验收：三类反馈、即时撤销/设置恢复、失败/慢请求、换号/退出、职业切换/换批/收藏/跳转、滚动/后台连续可见、桌面与窄屏遮挡/布局/动画。

现有 `DEEPSEEK_API_KEY` 检查为缺失；未执行真实模型联调，不请求聊天粘贴密钥。只记录有无，不输出凭据。

当前保留问卷/内容匹配基线及现有API；新采集修复已经在工作区并通过本地验证，尚未部署。第四阶段策略、负反馈与visible-v2仍默认关闭；第二阶段正式链路、第一阶段待审数据仍未启用。

继续实验所缺条件：核实数据源与测试账号；修复后的采集实际运行并积累可追溯时间、批次、位置和历史画像证据；完成浏览器验收；分版本满足用户/画像/规模/观察周期与质量门槛，再人工复核。当前不实施离线/影子行为算法，没有基线实验效果可报告，也未开启A/B测试。
