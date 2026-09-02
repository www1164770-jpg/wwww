# 知航屿推荐系统：Phase 2 真实数据观察日志

## 当前冻结版本

- Phase 1 算法版本：`phase1-v1`
- Phase 1 权重：occupation 20 / direction 30 / primary_need 35 / priority 10 / other_tags 5
- Phase 2.1：行为事件采集完成
- Phase 2.2 / 2.2-B / 2.2-C：指标、看板与数据质量诊断完成
- Phase 2.3：真实数据观察期，暂不启动
- Phase 2.2-D：观察期指标快照与算法版本对比基础完成

## 观察期固定口径

- 事件：`impression`、`click`、`favorite`、`repeat_visit`
- `repeat_visit` 窗口：30 分钟
- 推荐池：Top 60，前端保留 Top 48，每批 16 个确定性轮换
- 个性化来源比例只做观测，不强制 70/30
- 行为事件只做统计，不进入当前排序分数
- 不修改问卷、标签、候选池、排序权重或埋点定义

## Phase 2.3 启动门槛（首版观察阈值）

| 类别 | 条件 |
| --- | --- |
| 事件规模 | impression ≥ 1000、click ≥ 100、favorite ≥ 20、repeat_visit ≥ 10 |
| 画像覆盖 | 至少 3 个 occupation；至少 5 个 direction / primary_need 组合；每个主要画像曝光 ≥ 50 |
| 批次覆盖 | 至少 20 个有效 recommendation batch，且来自至少 2 个用户 |
| 数据质量 | 重复曝光率 < 2%；明显 click 双写 = 0；无效 website_id = 0；未知 event_type = 0 |
| 趋势稳定 | 能比较 7 天与 30 天窗口；数据周期较短时，按实际累计周期观察并记录 |

这些是数据观察门槛，不是推荐算法逻辑。是否进入 Phase 2.3 仍需结合 match_score、primary_need、tag 与 personalized/general 的行为趋势人工复核。

## 版本记录

推荐响应与行为事件 metadata 记录 `algorithm_version=phase1-v1`。未来启用行为融合时使用新的显式版本（例如 `phase2.3-v1`），不修改历史事件。

## 观察快照

管理员可在 `/admin/recommendation-metrics` 保存当前聚合结果。快照只保存
汇总 JSON、数据质量、readiness、match_score 分桶、primary_need、tag 和
personalized/general/fallback 指标，不复制或修改 `user_behavior_events`。

- `POST /api/recommendation/metrics/observation-snapshots`
- `GET /api/recommendation/metrics/observation-snapshots`
- `GET /api/recommendation/metrics/observation-snapshots/compare`

快照包含算法版本、观察范围、测试账号排除开关和捕获时间。当前仍为
`phase1-v1`；Phase 2.3 启动后使用新的显式版本，便于跨版本比较 CTR、收藏率和回访率。

## 测试账号

指标默认支持 `exclude_test_users=true`。测试账号只能通过显式环境变量 `RECOMMENDATION_METRICS_TEST_USER_IDS` 配置，不根据用户名或邮箱中是否包含 `test` 猜测。管理员可传 `exclude_test_users=false` 查看包含测试账号的数据。

## 观察记录

| 日期 | 算法版本 | 时间范围 | 事件规模 | 画像覆盖 | 数据质量 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-08-10 | phase1-v1 | 尚未开始真实积累 | 0（迁移后初始状态） | 待积累 | 待观察 | 不生成虚假行为数据 |
