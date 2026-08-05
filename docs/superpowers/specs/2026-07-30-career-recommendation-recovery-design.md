# 职业推荐恢复设计

日期：2026-07-30

## 目标

修复首页职业恢复、职业协议、推荐/分类请求状态与运行中旧后端造成的错误展示；以独立 `CareerSelector.vue` 替换旧的扁平职业区域，并扩展现有幂等 seed 以建立网站职业关联。

## 职业协议

前端界面显示中文，推荐接口只发送以下规范代码：

- `frontend_developer`：前端开发
- `backend_developer`：后端开发
- `ai_app_developer`：AI 应用开发
- `llm_engineer`：大模型工程师
- `product_manager`：产品经理
- `ui_ux_designer`：UI/UX 设计师
- `data_analyst`：数据分析师
- `operations`：运营
- `technical_operations`：技术运营
- `student`：学生
- `teacher`：教师
- `creator`：自媒体创作者
- `other`：其他

前端使用单一职业模块维护方向、中文标签和历史别名。后端使用单一职业模块将规范代码或历史值转换为规范代码，再映射为已有中文标签后查询。历史值 `programmer`、`designer`、`marketing`、`ecommerce`、`content_creator`、`self_media_creator` 继续兼容。空值和未知值返回无效结果，绝不降级为 `other`。

## 职业恢复

恢复优先级严格为：

1. 当前会话刚选择的有效职业；
2. 本地持久化的有效职业；
3. 已登录用户问卷中的有效职业；
4. 无职业选择。

未知本地值将被忽略并移除。只有用户明确选择“其他”时才持久化并请求 `other`。

## 页面结构与状态

首页主职业模块为左右布局：

- 左侧 `CareerSelector.vue` 是一个面板，内部在“职业方向”和“详细职业”两种状态间切换；不换路由。切换使用 200ms 左右的透明度和水平位移动画，并尊重 `prefers-reduced-motion`。
- 右侧标题为 `适合「中文职业」的网站工具`，继续复用 `SiteCard.vue`。
- 推荐网格桌面 3 列、中宽 2 列、手机 1 列。

推荐状态独立为 `idle/loading/success/empty/error`。分类状态独立为 `loading/success/empty/error`。请求失败显示错误和重试按钮；只有成功且数组为空时显示空状态。

## 数据流

`CareerSelector` 只产生规范职业代码。`Home.vue` 负责恢复、持久化、触发请求和展示状态。API 层只传输规范代码。后端入口统一规范化，再把代码映射为中文标签交给既有查询规则和 `site_occupations` 数据。

## Seed

在现有 `backend/scripts/seed_v1_demo_data.py` 中扩展 13 个职业和合理的网站关联。继续使用现有唯一约束和 `INSERT IGNORE`，保证重复执行不会产生重复关系。实现和验收期间不执行 seed，不清库，不改用户数据。

## 安全边界

- 不改无关业务逻辑，不更新依赖。
- 不执行 `git add`、`git commit`、`git push`。
- 不改变既有暂存文件状态。
- 只在测试完成后停止明确监听 5000 且属于本项目的旧 Python 进程。
- 新后端从当前工作区源码启动，随后验证健康检查和真实 API。

