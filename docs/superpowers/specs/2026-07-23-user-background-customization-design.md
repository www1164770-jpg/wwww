# User Background Customization Design

## 1. 功能目标与范围

登录用户拥有仅自己可见的背景图片库，并可把同一张图片分配给 `global`、`home`、`category`、`favorites`、`ai_assistant`、`profile` 六类界面。背景图片与显示参数随账号保存，换浏览器或设备登录后由 API 恢复。页面没有专属配置时继承 `global`；加载、下载或处理背景失败时，页面主要功能继续可用并使用系统默认背景。

本设计保持元数据表、私有图片 API 和前端 Blob 加载接口稳定，使磁盘实现可以在不改变前端调用语义的前提下替换为对象存储实现。

非目标：未登录用户持久背景、公共壁纸市场、GIF、SVG、视频、用户间共享、在线裁剪、滤镜、对象存储、按单个分类 ID 配置背景、动态视频壁纸、管理员审核壁纸。

## 2. 已审计的项目边界

### 2.1 后端

- Flask 实例在 `backend/app.py` 创建；`backend/wsgi.py:1-14` 只导入该实例作为安全 WSGI 入口。
- `backend/app.py:3101-3110` 在应用完成初始化后调用 `register_v1_routes(app, get_db_connection)`；所有新背景 API 放入 `backend/v1_routes.py` 的该注册函数内，避免在 `app.py` 增加第二套同路径路由。
- `backend/v1_routes.py:18-34` 的 V1 成功响应为 `{ code, legacy_code: 0, message, msg, data }`；`api_success(data, msg, status)` 和 `api_error(msg, code, status, data)` 是新 JSON API 的唯一响应封装。图片下载是二进制响应，不使用 JSON 包装。
- `backend/v1_routes.py:36-65` 的 `current_user_row()` 将 JWT identity 按用户名、邮箱、再按纯数字 `users.id` 查询，并过滤 `deleted_at IS NULL`。所有背景私有 API 都调用它，用户不存在统一返回 V1 `401`。
- 数据库同时使用 SQLAlchemy 模型和 PyMySQL 原生 SQL：`backend/models.py:5` 声明 `db = SQLAlchemy()`，`backend/db_pool.py:16-72` 提供 `DictCursor`、`autocommit=False` 的连接池，新 V1 路由以连接池和显式 `commit`/`rollback` 为准。
- SQLAlchemy URL 在 `backend/app.py:1193-1212` 配置为 MySQL/PyMySQL；真实数据库为 MySQL `8.0.45`。项目没有 Alembic 或 `migrations/` 目录，Schema 由 `backend/init_db.sql`、`backend/migration_extended.sql`、`backend/sql/*.sql` 和启动期兼容逻辑维护。
- `backend/v1_routes.py:86-98` 已有 `table_columns()` 运行时列缓存；背景功能不以它代替正式 DDL。
- 未发现现有 `request.files`、`secure_filename`、`MAX_CONTENT_LENGTH`、图片验证或安全下载实现。`requirements.txt` 和当前 `backend/venv` 均没有 Pillow。
- `backend/app_extensions.py:42-55` 的 `sanitize_log_data()` 会脱敏 Token、密码、验证码和密钥字段。背景模块新增日志只能记录 `background_id`、`user_id`、异常类型和操作阶段，不能记录 Token、原始文件名、绝对路径或二进制内容。

### 2.2 用户字段与现有壁纸

真实 `users` 表包含 `dark_mode tinyint(1)` 与 `custom_wallpaper text`；`backend/models.py:22-23` 也声明这两个字段。`backend/app.py:2219-2302` 的旧 `/api/user/sync` 和 `/api/user/settings` 可写入、读出 `custom_wallpaper`，但其格式不是 V1 响应，且读取按用户名参数而不是 `current_user_row()`。

前端 `backend/frontend/src/stores/app.js:37-55, 69-127` 只把 `customWallpaper`、`focusWallpaper` 和 `dark_mode` 保存到 localStorage；没有页面读取该值来渲染当前背景。`custom_wallpaper` 因此是遗留的 URL 字段，不适合作为私人图片库、页面继承或显示参数的存储位置。

新系统不继续读取或写入 `users.custom_wallpaper`。首次发布时执行一次独立迁移：仅当旧值是 `http` 或 `https` URL 时，后台在受控任务中下载、按新图片规则处理并写入一条 `user_backgrounds` 记录和一条 `global` 设置；下载、解码、配额或数据库任一步失败时保留旧字段、不创建半成品记录，并让用户继续看到系统默认背景。迁移任务完成后保留旧字段一个发布周期作为只读审计数据，不再由前端或背景 API 返回；下一个发布周期移除旧路由中的 `custom_wallpaper` 读写，字段删除另立 Schema 阶段处理。

### 2.3 前端

- `backend/frontend/src/App.vue:1-32` 当前根层是 `#app-root` 内的 `router-view`，随后是 Cookie 横幅和 Toast。`AppBackground` 应作为第一个根子节点插入、位于 `#app-root` 后方；`#app-root` 成为相对定位的内容层。
- `backend/frontend/src/main.js:8-18` 先安装 Pinia、初始化 `useUserStore()`，再安装 Router；背景 Store 采用同一 setup-store 风格并在 Router 安装前初始化认证监听。
- 路由定义在 `backend/frontend/src/router/index.js:8-65`：`/`、`/categories`、`/category/:id`、`/favorites`、`/profile` 是本设计的实际映射依据。
- `backend/frontend/src/components/layout/AppHeader.vue:38-75` 包含登录用户头像菜单，现有项目入口为 `/profile`、`/favorites` 和退出。背景设置只新增为同一菜单中的一个 `button[role=menuitem]`，不创建独立菜单或路由。
- `backend/frontend/src/components/ai/AiSiteAssistant.vue:15-26` 证明 AI 助手是覆盖层中的侧边 `aside`，不是路由页面；`ai_assistant` 仅渲染这个面板的内层背景，不改变面板背后的页面背景。
- `backend/frontend/src/utils/api.js:22-34,351-395` 的 Axios 实例自动携带认证请求头，成功响应返回完整 `response`，`unwrapResponse()` 负责展开 V1 `data`。图片请求必须使用此实例并设置 `responseType: "blob"`。
- `backend/frontend/src/stores/user.js:48-95` 的 `logout()` 清除统一认证会话并重置 Store；背景 Store 通过认证状态监听调用 `reset()` 和 `revokeAllObjectUrls()`，不改动 Authing、JWT 或 `user` Store 的核心逻辑。
- 固定背景位于 `backend/frontend/src/style.css:28-54` 的 `html`/`body` 以及 `.page`；首页 `.page` 在 `Home.vue:1185-1189`、分类详情在 `CategoryDetail.vue:272-298`、收藏在 `Favorites.vue:165-193`、个人中心在 `ProfileView.vue:246-275` 使用不透明背景。后续前端阶段只将页面根背景改为透明或低不透明度表面；搜索栏、网站卡片、筛选面板、导航和个人中心卡片保持不透明或高对比半透明表面，不能把整页内容强制透明。

## 3. 总体架构与数据流

系统由四个模块组成：私人图片库、页面配置、认证图片读取、前端背景渲染与设置面板。

```text
POST multipart file
→ 大小与 Pillow 内容验证
→ EXIF 方向修正、缩放、WebP 编码
→ 原子写入用户私有磁盘路径
→ 写入 user_backgrounds
→ GET /api/backgrounds 返回元数据
→ Axios responseType=blob 下载认证图片
→ URL.createObjectURL 缓存
→ AppBackground 或 AI 面板三层背景渲染
```

上传先完成临时文件处理和原子落盘，再开启数据库写入；数据库失败会删除刚写入的最终文件。磁盘写入失败时不写数据库。删除先提交数据库回退状态，再删除磁盘文件；磁盘删除失败只记录安全日志，数据库引用不恢复。

## 4. 页面类型、参数与继承

允许的 `page_type` 固定为：`global`、`home`、`category`、`favorites`、`ai_assistant`、`profile`。

`resolvePageType(route)` 的固定映射：

| 路由 | 结果 |
| --- | --- |
| `/` | `home` |
| `/categories`、`/category/:id` | `category` |
| `/favorites` | `favorites` |
| `/profile`、`/questionnaire` | `profile` |
| 其余 RouterView 页面，包括登录、搜索、网站详情和管理页 | `global` |

AI 助手不调用 `resolvePageType(route)`；其打开状态由现有 `aiAssistant` Store 驱动，面板读取 `ai_assistant` 设置。

默认参数固定为 `overlay_opacity: 0.36`、`blur_px: 0`、`position_x: 50`、`position_y: 50`、`size_mode: "cover"`。允许的 `size_mode` 是 `cover`、`contain`、`auto`。

图片与参数分别解析：

```text
图片：page.background_id → global.background_id → 系统默认背景
参数：page 的参数记录 → global 的参数记录 → 默认参数
```

页面记录存在且 `background_id` 为 `NULL` 时，仅图片继承 `global`，该页面记录中的遮罩、模糊、位置和缩放参数继续生效。删除页面设置记录后，图片和参数都继承 `global`。删除 `global` 设置记录后，图片和参数都回退到系统默认值。

浅色模式遮罩颜色为 `rgba(255,255,255, overlay_opacity)`；深色模式遮罩颜色为 `rgba(15,23,42, overlay_opacity)`。现有 `isDarkMode` 是 `backend/frontend/src/stores/app.js:12-16` 的本地状态，前端阶段把它作为遮罩颜色输入，不修改其现有持久化语义。

## 5. 数据库设计

真实库已在 `favorites`、`user_profiles` 等表使用外键，因此新表使用外键。`user_backgrounds.user_id` 使用 `ON DELETE CASCADE`；物理删除用户前，账户删除流程必须先安全删除该用户的背景文件，再删除用户行。`user_background_settings.background_id` 使用 `ON DELETE SET NULL`，使物理删除图片时配置安全回退；常规用户删除图片使用软删除并显式将引用置空。

每位用户最多 10 张 `status='active'` 图片。MySQL 无法以普通唯一索引表达该条件，上传事务先对对应 `users.id` 执行 `SELECT ... FOR UPDATE`，再计数 active 图片；达到 10 时返回 `409 background_library_full`，不写文件或记录。

建议 DDL，兼容当前 MySQL `8.0.45`：

```sql
CREATE TABLE user_backgrounds (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT NOT NULL,
  storage_path VARCHAR(255) NOT NULL,
  original_name VARCHAR(255) NOT NULL,
  mime_type VARCHAR(32) NOT NULL DEFAULT 'image/webp',
  file_size INT UNSIGNED NOT NULL,
  width SMALLINT UNSIGNED NOT NULL,
  height SMALLINT UNSIGNED NOT NULL,
  status ENUM('active', 'deleted') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_user_backgrounds_user_status_created (user_id, status, created_at),
  UNIQUE KEY uq_user_backgrounds_storage_path (storage_path),
  CONSTRAINT fk_user_backgrounds_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT chk_user_backgrounds_size CHECK (file_size > 0 AND file_size <= 10485760),
  CONSTRAINT chk_user_backgrounds_dimensions CHECK (width > 0 AND height > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE user_background_settings (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT NOT NULL,
  page_type ENUM('global', 'home', 'category', 'favorites', 'ai_assistant', 'profile') NOT NULL,
  background_id BIGINT UNSIGNED NULL,
  overlay_opacity DECIMAL(3,2) NOT NULL DEFAULT 0.36,
  blur_px TINYINT UNSIGNED NOT NULL DEFAULT 0,
  position_x TINYINT UNSIGNED NOT NULL DEFAULT 50,
  position_y TINYINT UNSIGNED NOT NULL DEFAULT 50,
  size_mode ENUM('cover', 'contain', 'auto') NOT NULL DEFAULT 'cover',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_user_background_settings_page (user_id, page_type),
  KEY idx_user_background_settings_background (background_id),
  CONSTRAINT fk_user_background_settings_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_background_settings_background
    FOREIGN KEY (background_id) REFERENCES user_backgrounds(id) ON DELETE SET NULL,
  CONSTRAINT chk_user_background_settings_overlay CHECK (overlay_opacity >= 0.00 AND overlay_opacity <= 0.70),
  CONSTRAINT chk_user_background_settings_blur CHECK (blur_px <= 20),
  CONSTRAINT chk_user_background_settings_x CHECK (position_x <= 100),
  CONSTRAINT chk_user_background_settings_y CHECK (position_y <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

`storage_path` 只存相对路径，如 `backgrounds/42/550e8400-e29b-41d4-a716-446655440000.webp`；`original_name` 仅用于界面显示，绝不参与磁盘路径。UUID 是唯一磁盘文件名。背景库列表只返回 `status='active'` 记录。

## 6. 文件存储和图片处理

`BACKGROUND_UPLOAD_ROOT` 是服务端配置项。开发环境默认根目录为 `Path(__file__).resolve().parent / "uploads"`，最终文件路径为 `backend/uploads/backgrounds/<user_id>/<uuid>.webp`；临时文件位于 `BACKGROUND_UPLOAD_ROOT / ".tmp"`。路径一律通过 `pathlib.Path` 组装并在解析后验证其位于根目录内，客户端只提交 multipart 文件而不能提交文件路径。用户目录在通过验证、写入前由服务端创建。

生产环境必须把 `BACKGROUND_UPLOAD_ROOT` 指向应用进程可写、可备份的持久卷。`.gitignore` 在实施阶段加入 `backend/uploads/`；本阶段不改动 `.gitignore` 或创建目录。本地磁盘不能用于无持久磁盘的 Vercel 或 Serverless 部署；在该环境发布前，存储适配器必须替换为对象存储。

上传接口固定为 `multipart/form-data`，文件字段名为 `file`。请求内容长度上限为 `10_485_760` 字节。仅接受 Pillow 识别为 JPEG、PNG 或 WebP 的内容；GIF、SVG、视频、扩展名伪装和解析失败文件返回 `422 invalid_background_image`。Pillow 在第一轮打开时执行 `verify()`，第二轮重新打开进行处理；`Image.MAX_IMAGE_PIXELS` 固定为 `20_000_000`，并把 `DecompressionBombWarning` 转为拒绝请求的错误。

处理顺序固定为：`ImageOps.exif_transpose()` 修正方向；等比例 `thumbnail((2560, 1440), Image.Resampling.LANCZOS)`；小图不放大；有透明通道的 PNG 转为 `RGBA` 并保留透明通道，无透明通道图片转为 `RGB`；保存为 WebP，`quality=84`、`method=6`。新 WebP 不复制 EXIF 或其他输入元数据，MIME 固定为 `image/webp`。任何异常删除临时文件；最终文件已落盘但数据库写入失败时删除最终文件；磁盘写入失败时不执行 INSERT。

## 7. 私有读取和 API

所有 JSON API 都有 `@jwt_required()` 并先调用 `current_user_row()`。用户不存在返回 `api_error("登录状态已失效，请重新登录", 401, 401)`。列表、读取、上传引用验证和配置保存的所有权查询必须包含 `user_id = current_user_row()["id"]` 与 `status='active'`；DELETE 为支持幂等重试，按同一 `user_id` 查询 active 或 deleted 记录，只有 active 记录执行状态和引用更新。

### 7.1 背景库

| 接口 | 请求与权限 | 成功响应与事务 | 错误与幂等性 |
| --- | --- | --- | --- |
| `GET /api/backgrounds` | JWT；无参数 | `api_success({"items": [...]})`，每项包含元数据但不含磁盘路径 | 401；只读且幂等 |
| `POST /api/backgrounds` | JWT；`multipart/form-data` 的 `file` | 锁定用户、计数、处理文件、INSERT active 记录、提交；返回 `api_success({"background": item}, "created", 201)` | 400 缺文件，409 满 10 张，413 超 10MB，422 图片无效，500 安全错误；非幂等 |
| `GET /api/backgrounds/<int:background_id>/image` | JWT；路径参数 | 从数据库记录推导路径，使用 `send_file` 返回 WebP，`Content-Type: image/webp`、`Cache-Control: private, max-age=300, no-transform` | 401、404 不存在/无所有权/文件丢失；只读且幂等 |
| `DELETE /api/backgrounds/<int:background_id>` | JWT；路径参数 | 锁定图片与引用设置，置相关 `background_id=NULL`、图片 `status='deleted'`，提交，再删除磁盘文件；返回 `api_success({"background_id": id, "deleted": true})` | 401、404；对已 deleted 图片返回 `deleted:false` 的 200，幂等 |

下载接口绝不公开 `/uploads/...` 静态地址，不接收客户端路径，不返回绝对路径。文件缺失只返回 404 与安全日志中的 ID；不输出原始文件名、Token 或真实路径。

### 7.2 页面配置

| 接口 | 请求与权限 | 成功响应与事务 | 错误与幂等性 |
| --- | --- | --- | --- |
| `GET /api/background-settings` | JWT；无参数 | `api_success({"settings": {...}, "defaults": {...}})`，返回原始持久配置 | 401；只读且幂等 |
| `PUT /api/background-settings/<page_type>` | JWT；路径必须是六个固定值；JSON 必须完整包含 `background_id`、`overlay_opacity`、`blur_px`、`position_x`、`position_y`、`size_mode` | 验证 background 属于当前用户且 active，按 `UNIQUE(user_id,page_type)` upsert，提交后返回该记录 | 400 非法参数，404 background 不存在，409 非本用户图片，401；相同请求幂等 |
| `DELETE /api/background-settings/<page_type>` | JWT；路径必须是六个固定值 | 删除一条配置记录；返回 `api_success({"page_type": type, "deleted": boolean})` | 400 非法页面类型，401；无记录时 `deleted:false`，幂等 |

PUT 保存 `background_id:null` 时保留该页面独立参数并继承 global 图片。DELETE `global` 时移除 global 图片与参数，所有未覆盖值使用系统默认。删除图片事务先更新引用设置，再标记图片 deleted，提交成功后再删除文件；磁盘删除失败只记录安全日志，不恢复设置引用。

## 8. 前端架构

建议在实施阶段新增下列文件：

| 文件 | 输入、输出与依赖 | 单一职责与禁止职责 |
| --- | --- | --- |
| `src/components/background/AppBackground.vue` | 输入 `backgroundStore.effectivePageBackground`；输出固定三层背景；依赖 `background` Store | 位于 RouterView 后方渲染图片、模糊复制层和遮罩层；不管理上传、表单或认证 |
| `src/components/background/BackgroundSettingsModal.vue` | 输入 `open`；输出 `close`、`saved`；依赖 background Store 与子组件 | 管理页面类型、草稿、保存、恢复、取消；不直接读写 Axios 或 Object URL |
| `src/components/background/BackgroundLibrary.vue` | 输入 active 图片和当前选择；输出 `select`、`upload`、`delete` | 列表、容量、缩略图和删除交互；不解析路由或渲染全局背景 |
| `src/components/background/BackgroundPreview.vue` | 输入草稿设置和 Blob URL；无持久输出 | 在弹窗或 AI 面板中预览三层背景；不提交配置或创建 URL |
| `src/stores/background.js` | 依赖 Pinia、Router、`api`、`user` Store 和 `utils/background.js` | 处理元数据、配置、Blob 缓存、草稿、请求和退出清理；不操纵 Header 菜单 DOM |
| `src/utils/background.js` | 输入 route、配置、URL 缓存键；输出 page type、默认值和有效设置 | 纯函数，包括 `resolvePageType()`、`resolveEffectiveBackground()`；不发网络请求或读 localStorage |

`App.vue` 将渲染 `<AppBackground />`、`#app-root`、Cookie 横幅和 Toast。背景层使用 `position:fixed; inset:0; z-index:0; pointer-events:none`；`#app-root` 使用 `position:relative; z-index:1`。图片层使用 `background-image`，模糊层使用独立伪元素或独立元素并限定在背景层，遮罩层独立覆盖。绝不对 RouterView 使用 `filter: blur()`。Header 的既有 `z-index:20`、Cookie 的 `z-index:99999`、弹窗和 AI 面板均在内容层之上。

AI 面板在 `AiSiteAssistant.vue` 内部使用与 `BackgroundPreview` 同一三层样式和 `backgroundStore.effectiveAiAssistantBackground`，只影响 `ai-site-assistant__panel`。页面背景仍由 AppBackground 按当前路由渲染。

背景 Store 的固定状态为：`library`、`settingsByPageType`、`objectUrlByBackgroundId`、`inflightByBackgroundId`、`draftByPageType`、`isSettingsModalOpen`、`loading`、`error`。固定方法为：`initializeForSession()`、`loadLibrary()`、`loadSettings()`、`fetchImageObjectUrl(backgroundId)`、`uploadBackground(file)`、`deleteBackground(id)`、`savePageSetting(pageType, setting)`、`deletePageSetting(pageType)`、`beginDraft(pageType)`、`applyDraft(pageType, draft)`、`discardDraft(pageType)`、`openSettingsModal()`、`closeSettingsModal()`、`resolveEffectivePageBackground(pageType)`、`revokeObjectUrl(id)`、`revokeAllObjectUrls()`、`reset()`。

同一个 `background_id` 的下载由 `inflightByBackgroundId` 复用 Promise，完成后缓存一个 Object URL。替换或删除图片时先 revoke 对应旧 URL；`userStore` 登出、背景 Store reset、AppBackground 卸载时调用 `revokeAllObjectUrls()`；请求失败不缓存 URL。预览只写 `draftByPageType`，保存成功后才更新 `settingsByPageType`，关闭或取消时丢弃草稿并恢复持久有效设置。

## 9. 设置入口、面板和回退

`AppHeader.vue` 的登录用户菜单新增“背景设置”按钮。它调用背景 UI Store 的单一 `openSettingsModal()`，然后关闭用户菜单；未登录用户不渲染该入口。375px 下沿用现有用户下拉菜单宽度与视口约束，菜单内容可换行但不得产生横向滚动。该入口不改变 `/profile`、退出登录、Authing 回调或 AI 助手入口。

设置面板包含：我的背景库、上传按钮、`0/10` 至 `10/10` 容量提示、缩略图、当前使用标记、删除按钮、页面类型选择、图片选择、遮罩滑块、模糊滑块、水平/垂直位置控制、缩放方式、实时预览、保存、恢复当前页面默认和关闭。恢复默认执行 `DELETE /api/background-settings/<page_type>`；关闭未保存草稿执行 `discardDraft()`，不请求 API。

删除未使用图片只将其标记 deleted 并删除文件。删除页面专属图片后对应配置 `background_id` 为空、保留该页参数，图片继承 global。删除 global 图片后 global 图片为空，所有继承页使用系统默认图片；各页面专属参数仍保留。数据库存在记录但文件丢失时下载返回 404，Store revoke 旧 URL、显示非阻塞提示并渲染系统默认背景。

## 10. 错误与可读性规则

配置请求失败使用默认参数和系统默认背景；Blob 下载失败、网络断开、文件 404、上传失败、数据库失败、磁盘失败和删除失败都不能使 RouterView 白屏。错误不能让登录、收藏、搜索或 AI 助手失效。上传与保存仅在 API 成功后显示成功提示，不能把后端错误显示成已保存。

页面根容器可透明以露出背景，但导航、搜索壳、网站卡片、筛选面板、个人中心 `.panel`、收藏/分类 Hero 和设置弹窗保持不透明或高对比 `rgba` 表面。遮罩始终渲染在背景图之上、内容层之下；文字颜色继续使用现有 CSS 变量。背景层 `pointer-events:none`，不得拦截点击、滚动、键盘或 AI 面板交互。

## 11. 测试设计

后端测试覆盖：未登录上传、正常 JPEG/PNG/WebP 上传、10MB 限制、伪装非图片、GIF/SVG、EXIF 旋转、WebP 输出、2560×1440 缩放、小图不放大、20,000,000 像素拒绝、10 张配额、用户隔离、私有读取、删除未使用和使用中图片、global 回退、参数边界、非法 `page_type`、文件缺失、数据库回滚和磁盘失败清理。

前端测试覆盖：头像菜单入口、Store 初始化、路由映射、Blob 请求、URL revoke、图片继承、参数继承、AI 面板背景、上传草稿、保存、取消、删除回退、恢复默认、退出登录、浅深色遮罩、375px、无横向溢出、背景层 `pointer-events:none`。构建回归包含搜索、收藏、分类、认证和 AI 助手既有静态验收。

## 12. 分阶段实施

### 阶段 1：数据库与背景图片库后端

前置条件：本设计已审阅，MySQL 8.0.45 可执行独立 Schema 脚本，Pillow 被明确加入依赖。

修改范围：背景表 DDL、模型或 SQL 访问层、上传/读取/删除路由、存储配置、后端测试、`.gitignore`。

交付与完成标准：两张表、10 张配额、验证/转码、私有 Blob 读取和删除回退路由均由测试覆盖；不实现页面配置或任何前端界面。

测试范围：上传、认证、私有读取、磁盘与数据库失败边界。

建议提交：`feat(background): add private background library backend`。

### 阶段 2：页面配置与继承接口

前置条件：阶段 1 的图片库 API 与测试通过。

修改范围：配置读写删除 API、参数验证、图片所有权验证、继承和删除回退服务、后端测试。

交付与完成标准：六种 page type 的原始配置可读写，图片/参数继承和 global 删除回退均通过测试；不渲染前端背景或设置面板。

测试范围：upsert、参数范围、null 图片继承、删除与幂等性。

建议提交：`feat(background): add per-page background settings`。

### 阶段 3：前端全局背景渲染

前置条件：阶段 1、2 API 通过真实认证验收。

修改范围：background Store、背景纯函数、AppBackground、App.vue 挂载、页面根表面、AI 面板内层背景、静态测试。

交付与完成标准：登录恢复、路由类型解析、Blob 缓存和退出 revoke 生效；AI 面板不覆盖页面背景；不提供用户设置入口或上传界面。

测试范围：继承、Object URL 生命周期、pointer-events、375px、构建和既有前端回归。

建议提交：`feat(background): render account backgrounds globally`。

### 阶段 4：背景设置界面与完整验收

前置条件：阶段 1 至 3 的接口和渲染均通过。

修改范围：Header 菜单入口、统一设置弹窗、背景库、上传、参数草稿、预览、保存、删除、恢复默认和响应式验收。

交付与完成标准：已登录用户可完整管理 10 张库、六类设置和草稿，关闭取消不污染持久状态；未登录无入口；不改变 Authing、收藏、AI 推荐算法或搜索菜单。

测试范围：所有面板交互、移动端、可读性、退出、真实 Blob 接口和完整回归。

建议提交：`feat(background): add background customization panel`。

## 13. 设计自审结论

字段、枚举、默认参数、API 路径和删除顺序在本文统一。`custom_wallpaper` 的遗留兼容、Blob 生命周期、磁盘局限、AI 面板隔离、Authing 与收藏边界均已明确。本文只记录设计、DDL 建议和阶段边界，不包含生产代码、数据库执行、依赖安装、上传目录创建或实施计划。
