# 职业推荐恢复实施计划

> 本计划在当前工作区直接执行。用户明确禁止暂存、提交和推送，因此所有常规提交检查点只记录 `git status`，不运行任何 Git 写操作。

## 任务 1：保护边界并建立失败测试

文件：

- 新建 `backend/frontend/scripts/verify-career-recommendation.mjs`
- 修改 `backend/frontend/package.json`
- 新建 `tests/test_occupation_utils.py`
- 修改 `tests/test_recommend_sort_v1.py`
- 修改 `backend/frontend/scripts/verify-home-ai-recommend.mjs`

步骤：

1. 记录 `git status --short` 和暂存文件列表。
2. 编写中文、规范代码、历史值、空值、未知值的职业规范化测试。
3. 编写选择器方向/返回状态测试。
4. 编写推荐和分类请求“失败/真实空”区分测试。
5. 编写后端规范代码映射到中文推荐规则的测试。
6. 运行新增测试并确认因功能缺失或旧行为而失败。

## 任务 2：实现集中职业协议

文件：

- 新建 `backend/frontend/src/utils/occupation.js`
- 新建 `backend/frontend/src/components/home/useCareerSelector.js`
- 新建 `backend/frontend/src/utils/listRequestState.js`
- 新建 `backend/occupation_utils.py`
- 修改 `backend/v1_routes.py`
- 修改 `backend/frontend/src/components/questionnaire/QuestionnaireForm.vue`

步骤：

1. 在前端模块集中维护职业方向、规范代码、中文标签和历史别名。
2. 在后端模块集中维护规范化与中文标签映射。
3. 推荐入口先规范化，再使用中文标签查询既有网站职业数据。
4. 问卷提交保存规范代码；已有历史值由读取端兼容。
5. 运行职业协议测试并确认通过。

## 任务 3：实现新版职业选择和首页状态

文件：

- 新建 `backend/frontend/src/components/home/CareerSelector.vue`
- 修改 `backend/frontend/src/views/Home.vue`
- 修改 `backend/frontend/src/components/home/CategorySection.vue`

步骤：

1. 建立同面板方向/详细职业切换、返回按钮和可访问键盘焦点。
2. 用新版左右模块替换旧职业展示，不保留重复旧标题。
3. 实现职业恢复优先级和有效值持久化。
4. 推荐接口统一发送规范代码。
5. 推荐状态实现 `idle/loading/success/empty/error`。
6. 分类状态实现 `loading/success/empty/error`，分别重试。
7. 网格响应式为 3/2/1，保留 `SiteCard` 既有交互样式。
8. 运行前端新增测试与首页回归测试。

## 任务 4：扩展幂等 seed

文件：

- 修改 `backend/scripts/seed_v1_demo_data.py`

步骤：

1. 补齐 13 个中文职业标签。
2. 为已有网站建立合理职业关联。
3. 保留 `INSERT IGNORE` 和唯一关系约束。
4. 仅静态检查 seed；不执行。

## 任务 5：回归验证

步骤：

1. 运行 `git diff --check`。
2. 运行 Python 职业测试、推荐测试和适用完整测试。
3. 运行：
   - `npm.cmd run build --prefix backend/frontend`
   - `npm.cmd run test:auth-state --prefix backend/frontend`
   - `npm.cmd run test:api-base-url --prefix backend/frontend`
   - `npm.cmd run test:home-ai-recommend --prefix backend/frontend`
   - 新增职业测试命令
4. 对 seed 和 Python 改动执行语法检查。

## 任务 6：运行时与浏览器验收

步骤：

1. 重新核对 5000 监听 PID、可执行文件和进程启动时间。
2. 只停止已确认属于本项目的旧 5000 进程。
3. 从当前工作区启动 Flask 后端。
4. 验证健康检查、分类和三个职业推荐的实际响应。
5. 浏览器验证无职业、方向切换、返回、职业切换、刷新恢复、错误/空状态、分类错误、卡片交互、3/2/1 响应式和控制台。
6. 最后记录 `git status --short`、暂存边界和 `git diff --stat`。

