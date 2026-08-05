# 知航屿

本仓库的实际应用由 Flask 后端和 Vue 3/Vite 前端组成：

- `backend/app.py`：本地 Flask 启动入口
- `backend/wsgi.py`：WSGI 入口
- `api/index.py`：Vercel Python Function 入口
- `backend/frontend/`：当前使用的前端项目
- `frontend/`、`wwww/`：历史资源或重复文件，不是当前启动入口

## 本地环境

在仓库根目录创建 Python 虚拟环境并安装依赖。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path backend\.env)) {
    Copy-Item backend\.env.example backend\.env
}
npm.cmd ci --legacy-peer-deps --prefix backend/frontend
```

macOS/Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
test -f backend/.env || cp backend/.env.example backend/.env
npm ci --legacy-peer-deps --prefix backend/frontend
```

编辑 `backend/.env`，至少确认 MySQL 配置；Redis、Meilisearch、邮件、
GitHub OAuth 按需配置。不要提交该文件。

如需覆盖前端 API 地址，将 `backend/frontend/.env.example` 复制为
`backend/frontend/.env.development` 后编辑。默认值适合本机后端的 5000
端口。

## 启动

从仓库根目录启动后端：

```bash
python backend/app.py
```

Windows PowerShell 启动前端：

```powershell
npm.cmd run dev --prefix backend/frontend
```

macOS/Linux 启动前端：

```bash
npm run dev --prefix backend/frontend
```

默认前端为 `http://127.0.0.1:5173`，后端 API 为
`http://127.0.0.1:5000/api`。`BACKEND_HOST`、`BACKEND_PORT`、
`FRONTEND_URL` 和 `VITE_API_BASE_URL` 可覆盖这些本地默认值。

## 部署

Vercel 项目的 Root Directory 应保持在仓库根目录，由 `vercel.json`
统一安装、构建前端并部署 `api/index.py`。完整环境变量和验证步骤见
`DEPLOY_VERCEL.md`。
