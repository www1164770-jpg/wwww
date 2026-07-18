# Vercel 全栈部署说明

本项目使用一个 Vercel Project 同时发布 Vue/Vite 前端和 Flask Python
Function。本文只记录配置方法，不包含任何真实密钥或生产域名。

## 1. 部署前准备

- 将准备发布的提交推送到 GitHub，并确认本地测试与前端构建通过。
- 准备允许 Vercel 访问的远程 MySQL。`DB_HOST` 不能使用 `localhost`，也不能使用
  `127.0.0.1`。
- 如果登录、验证码或一次性交换码使用 Redis，准备 Vercel 可访问的远程 Redis；不能使用本机 Redis。
- 准备 SMTP 发信账户和 Authing 应用配置。只在 Vercel Dashboard 中填写授权码和密钥。
- 不提交 `.env`、`.vercel/`、数据库导出、Token 或密码。

## 2. 导入项目

1. 在 Vercel 中导入当前 GitHub 仓库。
2. Root Directory 保持为仓库根目录（Dashboard 中留空），不要设置为 `backend/frontend`。
   否则 `api/index.py`、`backend/app.py` 和根目录
   `requirements.txt` 不在部署范围内。
3. 使用一个 Vercel Project，不拆分前端和 API，也不配置第二个外部 API 域名。
4. 构建配置由根目录 `vercel.json` 提供。若 Dashboard 保存过旧的覆盖值，应删除覆盖或改成与仓库配置一致。

当前构建设置：

```text
Install Command: npm ci --prefix backend/frontend
Build Command: npm run build --prefix backend/frontend
Output Directory: backend/frontend/dist
Python Function: api/index.py
```

`backend/frontend/package-lock.json` 已存在，因此安装使用 `npm ci`。生成的
`backend/frontend/dist` 是构建产物，不需要提交。

## 3. 路由架构

Vercel 按以下顺序处理项目路由：

1. `/api` 和 `/api/*` 重写到 `/api/index.py`，由同一个 Flask `app` 处理。
2. 已生成的静态文件（例如 `/assets/*` 和 favicon）由 Vercel 文件系统直接提供。
3. 其他页面路径重写到 `/index.html`，交给 Vue Router。

因此 `/api/health`、`/api/auth/me` 等不会被 SPA 回退吞掉；`/login`、`/profile`、
`/favorites` 和 `/admin/dashboard` 刷新时仍会获得前端 HTML。

前端生产环境默认使用同源 `/api`。同项目部署时，`VITE_API_BASE_URL` 保持未设置；
不要填写本地 `5000` 地址，也不需要额外后端域名。

## 4. 环境变量

分别为 Production 和 Preview 配置适合各自环境的值。只填写变量名对应的真实值到
Vercel Dashboard，不要把值写入 Git。

### 必填

| 变量 | 用途 |
| --- | --- |
| `DB_HOST` | 远程 MySQL 主机，不能使用 `localhost` 或 `127.0.0.1` |
| `DB_PORT` | MySQL 端口 |
| `DB_USER` | MySQL 用户 |
| `DB_PASSWORD` | MySQL 密码 |
| `DB_NAME` | MySQL 数据库名 |
| `FLASK_SECRET_KEY` | Flask 会话签名 |
| `JWT_SECRET_KEY` | JWT 签名 |
| `FRONTEND_URL` | 当前 Production 或 Preview 的前端来源 |
| `REDIS_URL` | 远程 Redis 连接地址；认证验证码和一次性交换流程需要 |
| `AUTHING_ISSUER` | Authing OIDC Issuer |
| `AUTHING_APP_ID` | Authing 应用 ID |
| `AUTHING_APP_SECRET` | Authing 应用 Secret |
| `AUTHING_REDIRECT_URI` | 当前环境的后端回调 URL，路径为 `/api/authing/callback` |

### 按功能选填

| 变量 | 用途 |
| --- | --- |
| `MAIL_SERVER`、`MAIL_PORT` | SMTP 服务地址和端口 |
| `MAIL_USERNAME`、`MAIL_PASSWORD` | SMTP 发信账户和授权码 |
| `CORS_ALLOWED_ORIGINS` | 额外允许的来源；同源部署通常不需要 |
| `MEILI_HOST`、`MEILI_MASTER_KEY` | 远程 Meilisearch |
| `GITHUB_CLIENT_ID`、`GITHUB_CLIENT_SECRET` | GitHub OAuth |
| `DEEPSEEK_API_KEY` | 对应 AI 功能 |

代码还兼容 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD` 和
`MYSQL_DATABASE` 这组别名；部署时选择一组数据库变量即可，不要混用冲突值。

### 本地或平台自动变量

- `VITE_API_BASE_URL`：同项目 Vercel 部署保持未设置，前端自动使用 `/api`。
- `VERCEL_ENV`：由 Vercel 自动提供。
- `FLASK_ENV`、`WERKZEUG_RUN_MAIN`、`AUTHLIB_INSECURE_TRANSPORT`：仅用于本地开发或测试，不作为生产密钥配置。

## 5. Authing 配置

源码的认证流程包含两个不同回调路径：

- Authing 控制台允许的后端回调 URL：`https://<部署域名>/api/authing/callback`，并将同一地址写入 `AUTHING_REDIRECT_URI`。
- 后端处理完成后返回的 Vue Router 页面：`https://<部署域名>/authing/callback`。

Production 和 Preview 使用不同域名时，需要在 Authing 控制台人工加入对应的允许回调 URL。
不要修改源码中的 Authing App ID、Secret、Host 或 Issuer 来适配部署。

## 6. 首次部署后验证

在对应部署域名逐项验证：

| 请求 | 预期 |
| --- | --- |
| `GET /` | 200，返回前端 HTML |
| `GET /login` | 200，返回前端 HTML，不是 Vercel 404 |
| `GET /api/health` | 200，返回 JSON，不访问数据库 |
| `GET /api/health/db` | 远程数据库配置正确时 200 JSON |
| `GET /api/sites/recommend` | 200 JSON |
| `GET /api/auth/me` | 未登录时 401 JSON |
| `GET /api/route-that-does-not-exist` | 后端 404，不是前端 `index.html` |

同时检查静态 JS/CSS 能加载、请求中没有 `/api/api/`、浏览器没有相关 CORS 或
Network Error。首次部署验证只读接口，不写入或修改生产数据。

## 7. 常见问题与日志

- SPA 刷新 404：确认 Root Directory 为仓库根目录，并检查最后一条 SPA rewrite。
- `/api` 返回 `index.html`：确认两条 API rewrite 位于 SPA fallback 之前。
- Function Module 导入失败：确认 `api/index.py`、`backend/` 和根目录 `requirements.txt` 未被排除。
- 缺少 Python 包：查看 Deployment 的 Build Logs，并与 `requirements.txt` 对照。
- MySQL 无法连接：确认远程网络允许 Vercel 访问，且 `DB_HOST` 不是本机地址。
- CORS 错误：同源部署不需要通配符；核对 `FRONTEND_URL` 和可选的 `CORS_ALLOWED_ORIGINS`。
- Authing 回调错误：核对 Dashboard 变量和 Authing 控制台允许的回调 URL 是否完全一致。
- 后端 500：在 Vercel Dashboard 打开对应 Deployment，进入 Functions，选择
  `api/index.py` 查看 Function Logs。日志和截图不得包含完整数据库 URI、Token 或密码。
- 修改环境变量后，需要重新部署才会进入新的构建和 Function 运行环境。

## 8. 回滚

在 Vercel Dashboard 的 Deployments 中选择上一个成功版本，执行 Promote 或平台提供的
回滚操作。回滚前检查数据库迁移兼容性；不要通过提交 `.vercel/` 或编造自动化按钮名称来回滚。
