# 前端本地验收清单

1. 启动后端。
2. 启动前端。
3. 打开首页。
4. 测试站内搜索。
5. 测试 Google / 必应 / 百度搜索。
6. 注册账号。
7. 登录账号。
9. 首次登录进入问卷。
10. 提交问卷。
11. 首页查看职业推荐。
12. 点击不同职业，推荐网站发生变化。
13. 打开分类导航。
14. 进入分类详情。
15. 使用标签、免费、地区、排序筛选。
16. 搜索网站。
17. 查看网站详情。
18. 访问官网。
19. 收藏网站。
20. 我的收藏查看收藏。
21. 取消收藏。
22. 发表评论和评分。
23. 进入个人中心。
24. 修改问卷。
25. 推荐结果变化。
26. 管理员登录后台。
27. 新增网站。
28. 编辑网站。
29. 删除网站。
30. 新增分类。
31. 新增二级分类。
32. 新增标签。
33. 合并重复标签。
34. 查看用户列表。
35. 禁用和解禁用户。
36. 审核评论。
37. 查看后台数据看板。
38. 检查普通用户不能访问后台。
39. 检查退出登录。

## 构建检查

前端：

```bash
npx prettier --write "src/**/*.{vue,js,css}"
npm run build
```

后端：

```bash
python -m py_compile app.py v1_routes.py recommend_service.py db_pool.py email_service.py models.py
```

提交前检查 `git status`，确认不要提交 `.env`、`backend/.env`、`backend/frontend/.env`、`node_modules`、`dist`、`meili_data`、`meili_fresh`、`meilisearch.exe`、`dump.rdb` 或任何包含密钥的文件。
