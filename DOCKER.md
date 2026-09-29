# 知航屿 Docker 开发环境

## 日常操作

打开 Docker Desktop（Linux containers），在项目根目录运行：

```powershell
docker compose up -d
docker compose ps
```

访问 http://localhost:5173。首次启动会自动构建镜像，后续启动复用镜像和数据。
结束开发：

```powershell
docker compose down
```

这会删除容器和项目网络，但保留数据库 Volume。下次 `up -d` 会复用数据。
当前工作区已经生成忽略提交的根目录 `.env`，其中使用随机的 Docker 专用密码。
新克隆的工作区需先复制 `.env.example` 为 `.env`，填写 `DB_PASSWORD`、
`MYSQL_ROOT_PASSWORD`、`DOCKER_MEILI_MASTER_KEY`（至少 16 字符）。不要提交真实密钥。
`backend/.env` 保留本机开发配置，Compose 读取其中邮件、OAuth 等设置，
然后显式覆盖容器中的数据库、Redis、Meilisearch 地址。

## 服务与端口

| 服务 | Windows 地址 | 容器内地址 |
| --- | --- | --- |
| frontend | http://localhost:5173 | frontend:5173 |
| backend | http://localhost:5000 | backend:5000 |
| mysql | 127.0.0.1:3307 | mysql:3306 |
| redis | 不发布宿主端口 | redis:6379 |
| meilisearch | 不发布宿主端口 | meilisearch:7700 |

宿主端口仅绑定回环地址，避免把开发调试器开放到局域网。
本机已有 MySQL 使用 3306，因此 Docker 使用 3307，不停止原服务。
端口冲突时在根 `.env` 修改 `FRONTEND_PORT`、`BACKEND_PORT`、
`MYSQL_PUBLISHED_PORT`，然后 `docker compose up -d`；不要终止其他程序。
容器内部端口保持固定，不受宿主映射端口影响。

浏览器请求 `/api/...`，由 Vite 转发到 `http://backend:5000`。
浏览器不解析 `backend` 服务名。本机不使用 Docker 时，Vite 仍默认代理到
`http://127.0.0.1:5000`，现有 Python 启动方式和 `backend/.env` 保持可用。
现有 `db_pool.py` 已支持 `DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD`，
且 `MYSQL_*` 优先；Compose 将根 `.env` 中的 DB 值映射到这些现有 MYSQL 变量。
容器主机固定为 `mysql`，避免被本机 `.env` 的 localhost 覆盖。

## 修改代码与依赖

直接编辑 Windows 下 `backend/frontend/src` 和后端 Python 文件并保存。
目录通过 bind mount 映射到容器，Vite 使用轮询监听以兼容 Windows；
Flask 保留 `python backend/app.py`，通过 `FLASK_DEBUG=1` 启用自动重载。
普通 Vue、JS、CSS、Python 修改不需要 build 或重启容器。

安装 npm 包（将 `包名` 替换为实际名称）：

```powershell
docker compose exec frontend npm install 包名 --legacy-peer-deps
docker compose build frontend
docker compose up -d --no-deps --force-recreate --renew-anon-volumes frontend
```

安装命令会同步修改宿主 `package.json` 和 `package-lock.json`。
前端 Linux `node_modules` 使用独立匿名 Volume，不能使用 Windows 的依赖目录；
重建前端时需要上面的 `--renew-anon-volumes`，否则旧依赖卷可能遮住新镜像依赖。
该命令只作用于 frontend，不操作 MySQL 数据卷。

安装 Python 包：将依赖写入**根目录 `requirements.txt`**，然后执行：

```powershell
docker compose build backend
docker compose up -d --no-deps backend
```

根 requirements 是 README 现有本地安装入口，比 backend/requirements.txt 更完整，
包含 Pillow 等实际依赖。镜像使用 Python 3.14（本机为 3.14.5）和 Node 24
（本机为 24.18.0），额外启用 PyMySQL 的 RSA 登录支持以连接 MySQL 8.4。
Dockerfile 或镜像构建相关配置变化也需要重建对应服务。
仅 Compose / 环境变量变化通常执行 `docker compose up -d` 即可。

## 数据安全与初始化

MySQL 数据保存在 Docker 命名卷 `zhihangyu_mysql_data`，容器路径 `/var/lib/mysql`。
这是 Docker Desktop Linux 虚拟磁盘中的数据，不是 Windows 本机 MySQL 数据目录。
Redis 和 Meilisearch 分别使用 `zhihangyu_redis_data`、`zhihangyu_meili_data`。
背景上传文件仍保存在宿主 `backend/uploads/backgrounds`。

Docker 使用独立的新数据库，**没有自动导入或修改原本机数据库**。
Docker 启动包装器仅在库内没有任何表时调用原有 `db.create_all()` 与
`init_db.run()`，后者先提交分类再导入网站，避免原连接池启动同步在空库上的外键失败。
随后以 `exec` 运行原命令 `python backend/app.py`。已有表的数据库跳过此步骤。
没有新增表模型、
未执行迁移 SQL、未执行删除/清空语句。原有启动同步会更新基础分类和补充缺失网站，
Flask 重载时也会按原逻辑执行。已有用户、收藏和人工维护数据不会自动出现在新库中。

仓库存在多份旧 SQL 和包含 `DROP TABLE` 的备份，未挂载到
`/docker-entrypoint-initdb.d`，避免误执行或引入过时表结构。
爬虫等模块的额外迁移仍按原项目流程单独管理，不自动应用。
若要迁移原有业务数据，应先导出并核验当前本机数据库备份，再在明确的目标库中恢复；
不要把历史 SQL 文件直接当作初始化脚本执行，也不要覆盖原数据库。

Volume 已初始化后，修改 `.env` 密码不会自动更改数据库中的密码；
应在备份后通过正常数据库账号管理同步修改，不能通过删卷“修复”认证失败。

**不要随便执行这些操作：**

- `docker compose down -v` / `docker compose down --volumes`：删除项目数据卷。
- `docker volume rm zhihangyu_mysql_data`：直接删除数据库数据。
- `docker volume prune -a`：可能删除已停止项目的命名数据卷。
- `docker system prune --volumes`：会清理符合条件的数据卷，不应用于日常关闭。
- Docker Desktop 的清空数据 / 恢复出厂设置：可能删除所有容器数据。

不要随意修改 Compose 的项目名 `zhihangyu`；改名会使用另一套卷，看起来像数据丢失。

## 验证与排障

```powershell
docker compose config --quiet
docker compose ps
docker compose logs --tail 100 frontend backend mysql
Invoke-RestMethod http://localhost:5173/api/health/db
docker volume inspect zhihangyu_mysql_data
```

`config --quiet` 验证配置且不输出密码；完整 `docker compose config` 会展开密钥，不要公开输出。
首次构建需要访问 Docker Hub、npm 和 PyPI。本次机器的 Windows 代理为 127.0.0.1:7897；
如果镜像认证超时，可在当前 PowerShell 会话中使用已运行的代理：

```powershell
$env:HTTP_PROXY = 'http://127.0.0.1:7897'
$env:HTTPS_PROXY = 'http://127.0.0.1:7897'
docker compose build
```

代理地址是本机环境的排障示例，不写入项目镜像或全局系统设置。
邮件、GitHub OAuth 和外部 AI API 仍需要原有有效密钥、回调地址及外网连接。

## 本次实测（2026-09-24）

- `docker compose config --quiet`、前后端镜像构建、`up -d --wait` 成功。
- frontend / backend / mysql / redis 健康检查通过，Meilisearch `/health` 返回 available。
- 浏览器首页正常渲染；经 5173 代理访问 `/api/health/db` 和 `/api/sites` 返回 200，
  后者返回真实数据库网站，总数 522。
- Windows 保存 CSS 与 Vue 文件后，浏览器无需刷新就收到 HMR 并更新 DOM；
  保存 Python 文件后，日志出现 `Detected change` 和 `Restarting with stat`。
  临时验证标记均已移除，原文件按字节恢复。
- 实际执行 `docker compose down` 后卷仍存在；再次启动后 522 个网站的
  ID、名称、URL、分类内容 SHA-256 与重启前一致。
- Docker 空库启动保护测试 3 项、现有后端环境配置测试 5 项、前端 API base 测试通过。
- 未迁移本机已有数据，也未验证真实邮件发送、OAuth 登录和付费 AI 调用。
