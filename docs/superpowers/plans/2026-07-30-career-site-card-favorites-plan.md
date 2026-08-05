# Career Site Card Favorites Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将首页职业推荐网站卡片改为简约信息卡，并复用现有后端收藏 API 提供可恢复的乐观收藏交互。

**Architecture:** 共享 `SiteCard` 增加仅由首页职业模块启用的 `career` 变体，默认卡片保持不变，避免影响收藏页、搜索页和分类页。首页集中加载后端收藏 ID、向卡片传入收藏状态，并在请求前乐观更新、失败时回滚；不新增 `localStorage` 收藏来源。

**Tech Stack:** Vue 3 Composition API、Vite、现有 Axios API 封装、Node.js 静态验证脚本。

## Global Constraints

- 不修改职业选择、职业规范化、推荐/分类请求、seed、登录注册或 API 基础地址。
- 不安装 npm 依赖，不新增第二套收藏系统。
- 保留 `website-card`、reveal 外层、黑色 hover、`translateY(-2px)`、focus 和 reduced-motion。
- 职业网站网格保持桌面 3 列、900px 以下 2 列、640px 以下 1 列。
- 不执行 `git add`、`git commit` 或 `git push`，不改变现有 31 个暂存文件。

---

### Task 1: Site card and favorites contract verification

**Files:**
- Create: `backend/frontend/scripts/verify-site-favorites.mjs`
- Modify: `backend/frontend/package.json`
- Test: `backend/frontend/scripts/verify-site-favorites.mjs`

**Interfaces:**
- Consumes: `SiteCard.vue` template/style source and `Home.vue` state/data-flow source.
- Produces: npm command `test:site-favorites`.

- [ ] **Step 1: Write the failing verification script**

The checks must assert:

```js
[
  "career variant is enabled by Home",
  "inline SVG star uses transparent default fill",
  "favorite star fills with currentColor and orange state",
  "favorite button uses @click.stop and emits toggle-favorite",
  "favorite button binds aria-label and aria-pressed",
  "name and URL links preserve target and rel",
  "no anchor/button nesting exists in the career template",
  "Home loads favoriteAPI.getFavorites",
  "Home updates state before awaiting add/remove",
  "Home rolls back state and shows a toast on failure",
  "website-card and black hover are preserved",
  "career grid remains 3/2/1 columns",
  "no localStorage favorite source is introduced",
]
```

- [ ] **Step 2: Register and run the new command**

Run:

```powershell
npm.cmd run test:site-favorites --prefix backend/frontend
```

Expected: FAIL because the career card variant, SVG star, API restoration and optimistic update do not exist yet.

### Task 2: Career card semantic template and styles

**Files:**
- Modify: `backend/frontend/src/components/site/SiteCard.vue`
- Test: `backend/frontend/scripts/verify-site-favorites.mjs`

**Interfaces:**
- Consumes: existing `site`, `favorited`, `favoritePending`, `visit` and `favorite` component contracts.
- Produces: prop `variant: "default" | "career"` and event `toggle-favorite(site)` for the career variant.

- [ ] **Step 1: Add the career template**

Use an `article.website-card` with:

```vue
<button
  type="button"
  class="site-favorite-button"
  :class="{ 'is-favorite': isFavorited }"
  :aria-label="favoriteAriaLabel"
  :aria-pressed="isFavorited"
  @click.stop="handleFavoriteClick"
>
  <svg aria-hidden="true"><path /></svg>
</button>
```

The icon, name and display URL use independent anchors with `target="_blank"`, `rel="noopener noreferrer"` and `@click.prevent="openSite"`. Description falls back to `暂无网站简介`; tags use `visibleTags`, which is capped at three.

- [ ] **Step 2: Add computed display data**

Add:

```js
const isCareerVariant = computed(() => props.variant === "career");
const normalizedSiteUrl = computed(() => normalizeUrl(props.site?.url));
const displayUrl = computed(() =>
  normalizedSiteUrl.value
    .replace(/^https?:\/\//i, "")
    .replace(/\/+$/, ""),
);
```

`handleFavoriteClick()` emits `toggle-favorite` only for the career variant. The existing default favorite event remains unchanged.

- [ ] **Step 3: Add scoped minimalist styles**

The career modifier uses white background, `1px solid #dfe3e8`, `18px` radius, `22px` padding, 48px icon, two-line description, pill tags and an absolute 34px star button. The shared hover/focus styles remain on `.website-card`; reduced motion removes transforms.

- [ ] **Step 4: Run the focused verifier**

Run:

```powershell
npm.cmd run test:site-favorites --prefix backend/frontend
```

Expected: card structure/style checks pass; Home API state checks may still fail.

### Task 3: Existing API favorite restoration and optimistic updates

**Files:**
- Modify: `backend/frontend/src/views/Home.vue`
- Test: `backend/frontend/scripts/verify-site-favorites.mjs`

**Interfaces:**
- Consumes: `favoriteAPI.getFavorites/addFavorite/removeFavorite`, `unwrapList`, `errorToast`, `successToast`.
- Produces: `favoriteSiteIds`, `isSiteFavorited(site)`, `loadFavoriteState()`, `setSiteFavoriteState(site, value)`.

- [ ] **Step 1: Enable the career variant**

Home passes:

```vue
variant="career"
:favorited="isSiteFavorited(site)"
@toggle-favorite="toggleFavorite"
```

- [ ] **Step 2: Restore favorites from the existing API**

When logged in, call `favoriteAPI.getFavorites()`, derive normalized string IDs, and synchronize matching site objects. A load failure preserves API-provided `site.is_favorited` values and does not crash the page.

- [ ] **Step 3: Make toggle optimistic and recoverable**

Capture the previous value, update the matching site and ID set immediately, then await add/remove. On rejection, restore the previous state and show `操作失败，请稍后重试`.

- [ ] **Step 4: Synchronize newly loaded occupations**

After a career response succeeds, apply the loaded favorite ID set to returned sites so switching occupations retains star state.

- [ ] **Step 5: Run focused and career regression tests**

Run:

```powershell
npm.cmd run test:site-favorites --prefix backend/frontend
npm.cmd run test:career-recommendation --prefix backend/frontend
npm.cmd run test:home-ai-recommend --prefix backend/frontend
```

Expected: PASS.

### Task 4: Full verification and Chrome acceptance

**Files:**
- Verify only; no additional production file is planned.

- [ ] **Step 1: Run repository and frontend checks**

```powershell
git diff --check
npm.cmd run build --prefix backend/frontend
npm.cmd run test:auth-state --prefix backend/frontend
npm.cmd run test:api-base-url --prefix backend/frontend
npm.cmd run test:home-ai-recommend --prefix backend/frontend
npm.cmd run test:career-recommendation --prefix backend/frontend
npm.cmd run test:site-favorites --prefix backend/frontend
```

- [ ] **Step 2: Use real Chrome**

Verify the card at 1280px, 800px and 390px; confirm star toggle/re-toggle, no navigation from the star, link navigation, occupation switching, refresh restoration, keyboard focus, hover border/translation and clean console.

- [ ] **Step 3: Re-check the Git boundary**

Confirm staged file count and staged file list exactly match the initial 31-file snapshot. Report `git diff --stat` and all existing or environment-blocked failures without staging or committing.
