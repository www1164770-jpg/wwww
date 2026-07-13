# V1.0 认证闭环整改设计

## 目标

在不改变现有登录、注册和首页视觉布局、不触碰非认证业务的前提下，完成本地注册/登录、Authing 登录、退出、JWT 刷新、路由守卫和认证状态恢复的统一闭环。

## 现状与根因

- `token` 与 `access_token` 被多个前端文件交替读取，Pinia 只恢复 `access_token`，路由和请求拦截器的优先级也不一致。
- 登录页、Authing 回调、Pinia、Axios、顶部菜单和问卷页各自维护保存/清理列表，退出或 401 时容易残留认证字段。
- Axios 当前遇到 401 直接清理并跳转，没有单次刷新、并发合并和登录/注册接口排除。
- 后端标准刷新接口是 `/api/auth/refresh`，同时保留旧 `/api/refresh`，前端需要固定主路径并避免刷新接口自循环。
- Authing 回调当前把项目 JWT 放入前端 URL；用户信息还依赖后续 profile 请求，失败时可能留下不完整认证状态。
- 注册接口在输入规范化、邮箱校验、Redis 异常和邮件失败后的验证码清理上不完整。

## 设计方案

### 1. 统一前端认证状态

新增 `backend/frontend/src/utils/auth.js`，只依赖 `localStorage` 和浏览器事件，不依赖 Pinia，避免循环依赖。

```text
AUTH_STORAGE_KEYS = {
  legacyToken: "token",
  accessToken: "access_token",
  refreshToken: "refresh_token",
  user: "user",
  userInfo: "user_info",
  userRole: "user_role",
  questionnaireCompleted: "questionnaire_completed",
  isLoggedIn: "is_logged_in"
}
```

提供 `saveAuthSession(session)`、`clearAuthSession()`、`getAccessToken()`、`getRefreshToken()`、`isValidAuthToken()`、`normalizeAuthSession()`。`access_token` 是主状态；登录成功仍同步写入 `token` 作为兼容别名；如果只有格式有效的旧 `token`，首次读取时迁移到 `access_token`。清理逻辑一次性删除八个认证 key，并发布状态变更事件。

Pinia `user` store 使用上述工具恢复、保存和清理状态，补齐角色和问卷状态，并保留现有对外方法。所有退出入口最终调用 store 的 `logout()`，该方法先 `clearAuthSession()` 再恢复默认 Pinia 状态。

### 2. 本地登录与当前用户接口

`POST /api/auth/login` 继续支持用户名/邮箱，统一规范化账号，空参数返回 400，错误凭证返回 401，频率限制返回 429。成功响应在 `data` 中返回完整 `AuthSession`：

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "user_info": {"id": 1, "username": "...", "email": "...", "avatar": "..."},
  "user_role": "user",
  "questionnaire_completed": false
}
```

保留旧顶层字段兼容旧组件。新增或保留 JWT 保护的 `GET /api/auth/me`，只返回当前用户的 `user_info`、真实 `user_role` 和问卷状态。前端界面可以读取本地角色做导航拦截，但服务端管理员接口继续从 JWT 身份和数据库角色校验权限。

### 3. Authing 一次性交换码

Authing 授权码交换和用户同步仍在后端完成，凭证值不变。授权开始时先用站内相对路径规范化 `redirect`，将其和随机 `state`/`nonce` 绑定到 Flask session。

成功同步本地用户后，后端生成 `secrets.token_urlsafe(32)` 作为一次性交换码，有效期 60 秒。Redis 只保存最小数据（项目用户 ID 和已校验的站内 redirect），不保存 Authing access token、密码或密钥。回调只把 opaque exchange code 和安全 redirect 传给前端，不把项目 JWT 或用户信息放入 URL。

`POST /api/authing/exchange` 使用 Redis 原子 GETDEL（或等价 Lua 原子操作）取出并删除 code；无效、重复或过期 code 返回明确 400/401，Redis 异常返回 503，不降级为 URL token。交换成功后根据本地用户生成项目 access/refresh token，并返回与本地登录一致的 `data` AuthSession。前端 Authing Callback 使用同一 `saveAuthSession`，成功后按问卷状态跳转到问卷、合法 redirect 或首页。

### 4. Refresh Token 与 Axios 401

前端业务请求只带 `getAccessToken()` 返回的 access token。响应 401 时：

```text
普通业务请求 + 未重试 + 有 refresh_token
  -> 复用同一个 refreshPromise
  -> POST /api/auth/refresh（跳过认证拦截）
  -> 保存新 access_token
  -> 原请求只重试一次
```

登录、注册、发送验证码、Authing exchange、refresh、logout 等认证端点不进入自动刷新。刷新失败只执行一次 `clearAuthSession()`，所有并发等待请求统一失败并跳转登录页；不会产生无限 401 或 refresh 自循环。

后端主刷新接口使用 `verify_jwt_in_request(refresh=True)`，只接受 Refresh Token，Access Token 冒充时返回 401。旧 `/api/refresh` 保留为兼容别名。

### 5. 注册与验证码

注册和发送验证码均使用 JSON 安全读取、trim 用户名和邮箱，服务端校验邮箱格式、密码至少 8 位和验证码必填。注册前明确查询用户名/邮箱重复并返回对应提示；只有事务提交成功后删除验证码。发送验证码仅在邮件成功后写入 Redis，验证码 TTL 为 300 秒；Redis 异常返回服务不可用状态，SMTP 凭证不改。

## 测试策略

- 新增 Python unittest 认证测试，使用 fake connection/Redis 验证登录、注册、刷新、Authing exchange、并发单次兑换和管理员鉴权。
- 新增前端 Node smoke test，不引入 Vitest，验证 `saveAuthSession`、`clearAuthSession`、旧 token 迁移和退出后无残留。
- 运行后端 `py_compile`、现有 Python 测试、新增认证测试、前端认证 smoke test 和 `npm run build`。
- Redis、MySQL、SMTP、Authing 未配置或不可用时，测试明确记录为外部联调未完成，不伪称真实闭环通过。

## 范围约束

- 不修改首页、搜索、搜索引擎选择器、分类、职业推荐、热门网站和 AI 助手。
- 不修改任何 Authing、SMTP、数据库真实凭证。
- 不删除现有 Authing 集成，不大规模重构 `app.py`，只增加认证所需的局部函数和路由。
- 不自动 push GitHub。
