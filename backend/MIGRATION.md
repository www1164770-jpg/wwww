# 智汇 V1.0 数据库迁移说明

本项目的评论、评分、举报、DMCA、行为日志和推荐日志依赖 `backend/migration_extended.sql`。

## 执行步骤

1. 先备份当前数据库。
2. 在 MySQL 中执行迁移：

```bash
mysql -u root -p nav_site < backend/migration_extended.sql
```

如果你的数据库名不是 `nav_site`，请替换为实际库名。

3. 重启 Flask 后端。
4. 验证接口：

```bash
curl http://127.0.0.1:5000/api/nav-data
curl http://127.0.0.1:5000/api/admin/overview
curl http://127.0.0.1:5000/api/admin/comments
```

## 说明

- Redis 可选；未启动时导航、搜索和排行榜会自动降级，不应导致首页 500。
- 不要把 `.env`、外部 API Key、日志、构建产物提交到版本库。
- 已建议忽略：`__pycache__/`、`backend/logs/`、`backend/frontend/dist/`、`backend/venv/`。
