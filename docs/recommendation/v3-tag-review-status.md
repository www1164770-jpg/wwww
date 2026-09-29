# V3 标签体系审核状态

> 2026-09-25 收尾复核：下文为历史快照，不能代表当前落库状态。39 条获批记录已有 23 条可靠映射（20 条需新增关联、3 条重复审核无需单独迁移），16 条未解决。可靠部分为 30 个唯一关联，其中 1 个已有、29 个待新增。未执行正式落库，未批准新候选。详见 [第一阶段结果](stage1-resource-quality.md)、[映射预览](v3-tag-identity-20260925/mapping-preview.json) 和 [当前迁移预览](v3-tag-identity-20260925/current-db-preview.json)。

为避免与推荐系统的行为融合阶段混淆，标签线使用以下阶段名称：

- **V3 标签体系 Phase 2.1：候选预览完成**（只读，46 条）
- **V3 标签体系 Phase 2.2：审核队列完成**
- **V3 标签体系 Phase 2.2-A：人工审核**（当前阶段）
- **V3 标签体系 Phase 2.3：批准标签落库**（审核校验通过后才允许生成迁移预览）
- **推荐系统 Phase 2.3：行为画像融合**（仍未启动）

## 当前快照

- Questionnaire V3：代码完成
- V3 信号覆盖分析：完成
- V3 标签候选：46
- V3 标签审核：46/46 已审核，39 条至少有一个标签获批，7 条整条拒绝
- 正式标签写库：0
- Phase 1 权重：冻结
- `algorithm_version`：`phase1-v1`
- 推荐系统 Phase 2.3 行为融合：关闭
- V3 真实登录链路：仍待验收

审核记录固定检查网站能力、标签粒度、画像污染风险和证据可解释性。审核记录允许只批准 `suggested_tags` 的子集；`approved` 仅表示至少一个标签获批，不代表整条建议全部通过。

审核总结见 [`v3-tag-review-summary.json`](./v3-tag-review-summary.json)，原始审核队列见 [`v3-tag-review-queue.json`](./v3-tag-review-queue.json)。在执行任何 INSERT 前，必须重新验证总结中的状态和集合约束，并先生成 SQL Preview 与 Rollback Preview。
