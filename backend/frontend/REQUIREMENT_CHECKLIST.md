# 需求文档功能验收清单

## V1.0 必须实现

| 功能 | 当前状态 | 涉及文件 | 是否完成 | 需要修复的问题 |
| --- | --- | --- | --- | --- |
| 用户注册 | 本地账号直接注册，前端有防重复提交 | `backend/app.py`, `src/views/Register.vue`, `src/utils/api.js` | 是 | 继续保持密码哈希与中文错误提示 |
| 用户登录 | 支持邮箱或用户名登录，保存 token 与用户信息 | `backend/app.py`, `src/views/Login.vue`, `src/router/index.js` | 是 | 旧组件仍有 `code === 0` 兼容逻辑，需长期统一 |
| 用户退出 | 后端提供登出接口，前端清理本地登录态 | `backend/v1_routes.py`, `src/components/layout/AppHeader.vue` | 是 | 需人工验收顶部菜单清理 `questionnaire_completed` |
| 首次登录问卷 | 登录后可进入问卷，提交写入用户画像 | `backend/v1_routes.py`, `src/views/Questionnaire.vue` | 是 | 后台问卷配置已补入口，需联调真实库 |
| 问卷修改 | 个人中心可查看和修改问卷 | `backend/v1_routes.py`, `src/views/ProfileView.vue`, `src/views/Questionnaire.vue` | 是 | 修改后推荐变化需结合演示数据验收 |
| 职业推荐网站 | `/api/sites/recommend` 支持职业推荐与兜底排序 | `backend/recommend_service.py`, `backend/v1_routes.py`, `src/views/Home.vue` | 是 | 推荐规则后台已补入口，算法可继续接入更多权重 |
| 首页导航 | 首页包含搜索、分类、推荐、热门、最新和工具区 | `src/views/Home.vue`, `src/components/home/*.vue` | 是 | 源码中部分历史中文文案存在乱码，建议单独机械修复 |
| 分类导航 | `/api/categories` 返回父子分类，前台有分类页 | `backend/v1_routes.py`, `src/views/Categories.vue` | 是 | 需要真实数据保证每类至少 4 个网站 |
| 分类详情 | 支持分类下网站展示和筛选排序 | `backend/v1_routes.py`, `src/views/CategoryDetail.vue` | 是 | 无数据时依赖前端兜底网站 |
| 网站详情 | 展示网站字段、收藏、访问、相似网站和评论 | `backend/v1_routes.py`, `src/views/SiteDetail.vue` | 是 | 管理员评语字段暂无独立结构 |
| 搜索功能 | 支持站内搜索、联想、热门关键词和行为记录 | `backend/v1_routes.py`, `src/views/SearchResults.vue`, `src/components/common/SearchBar.vue` | 是 | 搜索热词依赖行为数据积累 |
| 收藏功能 | 支持收藏、取消收藏、备注和列表移除 | `backend/v1_routes.py`, `src/views/Favorites.vue`, `src/components/site/SiteCard.vue` | 是 | 未登录跳转需浏览器验收 |
| 个人中心查看收藏 | 个人中心与收藏页均可查看相关数据 | `backend/v1_routes.py`, `src/views/ProfileView.vue`, `src/views/Favorites.vue` | 是 | 浏览历史依赖行为数据 |
| 后台网站管理 | 支持增删改、状态、标签、职业和推荐等级 | `backend/v1_routes.py`, `src/views/admin/AdminSites.vue` | 是 | 批量导入入口仍可继续增强 |
| 后台分类管理 | 支持一级/二级分类增删改和状态 | `backend/v1_routes.py`, `src/views/admin/AdminCategories.vue` | 是 | 删除前风险提示可继续细化 |
| 后台标签管理 | 支持标签增删改与使用次数查看 | `backend/v1_routes.py`, `src/views/admin/AdminTags.vue` | 是 | 合并重复标签需结合数据表再增强 |

## V1.1 优化功能

| 功能 | 当前状态 | 涉及文件 | 是否完成 | 需要修复的问题 |
| --- | --- | --- | --- | --- |
| 评论评分 | 用户评论与评分、管理员审核接口已接入 | `backend/v1_routes.py`, `src/views/SiteDetail.vue`, `src/views/admin/AdminComments.vue` | 是 | 评论状态目前兼容 `visible/approved/rejected` |
| 推荐理由 | 推荐结果包含 `reason` | `backend/recommend_service.py`, `backend/v1_routes.py`, `src/components/site/SiteCard.vue` | 是 | 职业化文案可继续接入后台模板 |
| 搜索联想 | `/api/search/suggest` 已提供 | `backend/v1_routes.py`, `src/components/common/SearchBar.vue` | 是 | 需真实数据验证质量 |
| 热门关键词 | `/api/search/hot-keywords` 已提供 | `backend/v1_routes.py`, `src/views/SearchResults.vue` | 是 | 依赖搜索行为记录 |
| 用户行为记录 | click/favorite/search 已记录，失败不阻塞主流程 | `backend/v1_routes.py` | 是 | `unfavorite/dislike` 可继续补充更细事件 |
| 网站点击统计 | 访问官网时记录点击 | `backend/v1_routes.py`, `src/views/SiteDetail.vue`, `src/views/Home.vue` | 是 | 统计失败不阻止打开官网 |
| 后台数据看板 | 展示用户、网站、点击、收藏、职业和分类统计 | `backend/v1_routes.py`, `src/views/admin/AdminDashboard.vue` | 是 | 留存数据为简化统计，可继续扩展 |
| 后台问卷管理 | 本轮新增基础页面和接口 | `backend/v1_routes.py`, `src/views/admin/AdminQuestionnaires.vue` | 是 | 需要线上数据联调 |
| 后台推荐规则管理 | 本轮新增基础页面和接口 | `backend/v1_routes.py`, `src/views/admin/AdminRecommendRules.vue` | 是 | 推荐算法可继续逐步读取更多规则 |
| 后台设置 | 本轮新增基础页面和接口 | `backend/v1_routes.py`, `src/views/admin/AdminSettings.vue` | 是 | 设置项暂为基础配置 |
