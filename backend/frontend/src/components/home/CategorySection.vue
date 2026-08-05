<template>
  <section class="home-section category-section">
    <header class="category-heading reveal-on-scroll">
      <p>热门分类</p>
      <h2>按分类浏览网站资源</h2>
      <span>从学习、设计、开发到效率办公，快速找到适合你的网站工具。</span>
    </header>

    <div class="category-filter-bar" aria-label="网站分类栏">
      <div class="category-filter-bar__label">
        <span class="category-filter-bar__icon" aria-hidden="true">
          <Layers />
        </span>
        <span class="category-filter-bar__copy">
          <strong>网站分类</strong>
          <small>{{ activeCategoryDescription }}</small>
        </span>
      </div>

      <nav class="category-nav" aria-label="网站分类">
        <button
          v-for="category in categoryOptions"
          :key="category.name"
          type="button"
          class="category-tab"
          :class="{ 'category-tab--active': activeCategory === category.name }"
          :aria-pressed="activeCategory === category.name"
          @click="handleCategoryChange(category.name)"
        >
          <component :is="categoryIcon(category.name)" aria-hidden="true" />
          <span>{{ category.name }}</span>
        </button>
      </nav>
    </div>

    <div
      v-if="status === 'loading' && !allWebsites.length"
      class="website-skeleton-grid"
      aria-label="正在加载网站资源"
    >
      <article v-for="index in 8" :key="index" class="website-skeleton-card">
        <span></span>
        <b></b>
        <i></i>
      </article>
    </div>

    <div
      v-else-if="status === 'error' && !allWebsites.length"
      class="category-request-state category-request-state--error"
      role="alert"
    >
      <strong>网站分类加载失败</strong>
      <span>{{ error || "请检查网络连接后重试。" }}</span>
      <button type="button" @click="$emit('retry')">重新加载</button>
    </div>

    <EmptyState
      v-else-if="status === 'empty' && !allWebsites.length"
      title="暂无分类"
      description="分类请求成功，但当前没有可展示的网站资源。"
    />

    <template v-else>
      <div
        v-if="loadingCategorySites && !allWebsites.length"
        class="website-skeleton-grid"
        aria-label="正在加载分类网站"
      >
        <article v-for="index in 8" :key="index" class="website-skeleton-card">
          <span></span>
          <b></b>
          <i></i>
        </article>
      </div>

      <div v-else>
        <div
          v-if="refreshing || loadingCategorySites"
          class="category-request-note"
          role="status"
        >
          正在更新分类网站资源…
        </div>

        <div
          v-if="error && allWebsites.length"
          class="category-request-note category-request-note--error"
          role="status"
        >
          {{ error }}
        </div>

        <div class="website-grid-state">
          <div class="website-grid-toolbar">
            <p>{{ activeCategory }} · {{ visibleWebsiteCount }} 个网站</p>
          </div>

          <div v-if="filteredWebsites.length" class="website-card-grid">
            <SiteCard
              v-for="website in renderedWebsites"
              :key="websiteKey(website)"
              :site="website"
              variant="category"
              hide-actions
            />
          </div>

          <button
            v-if="renderedWebsites.length < filteredWebsites.length"
            type="button"
            class="website-load-more"
            @click="loadMoreWebsites"
          >
            加载更多网站
          </button>

          <div
            v-if="!filteredWebsites.length"
            class="category-empty-state"
            role="status"
          >
            <span class="category-empty-state__icon" aria-hidden="true">⌂</span>
            <h3>该分类暂无网站资源</h3>
            <p>可以切换其他分类，或稍后再来查看最新收录的网站。</p>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import {
  BookOpen,
  Bot,
  Code2,
  Compass,
  Folder,
  GraduationCap,
  Image,
  Layers,
  Lightbulb,
  Palette,
  PenTool,
  Star,
  Users,
  Zap,
} from "lucide-vue-next";
import { computed, ref } from "vue";
import EmptyState from "../common/EmptyState.vue";
import SiteCard from "../site/SiteCard.vue";
import { normalizeWebsite } from "../../utils/api";

const props = defineProps({
  categories: { type: Array, default: () => [] },
  categorySitesMap: { type: Object, default: () => ({}) },
  loadingCategorySites: { type: Boolean, default: false },
  refreshing: { type: Boolean, default: false },
  status: { type: String, default: "loading" },
  error: { type: String, default: "" },
});

defineEmits(["retry"]);

const PAGE_SIZE = 25;
const activeCategory = ref("全部");
const visibleLimit = ref(PAGE_SIZE);

const CATEGORY_ICON_MAP = {
  常用推荐: Star,
  框架文档: BookOpen,
  灵感采集: Lightbulb,
  原型设计: PenTool,
  开发社区: Users,
  "UI 组件库": Layers,
  AI工具: Bot,
  编程开发: Code2,
  设计资源: Palette,
  效率办公: Zap,
  学习成长: GraduationCap,
  数据分析: Compass,
  产品运营: Layers,
  素材资源: Image,
};

const categoryById = computed(() => {
  const result = new Map();
  props.categories.forEach((category) => {
    result.set(String(category.id), category);
  });
  return result;
});

function websiteKey(website = {}) {
  return String(
    website.renderKey ?? website.id ?? website.url ?? website.name ?? "",
  );
}

function normalizeCategoryKey(value) {
  const normalized = String(value ?? "")
    .trim()
    .toLowerCase();
  return !normalized || normalized === "all" || normalized === "全部"
    ? "all"
    : normalized;
}

function getWebsiteCategoryName(website = {}) {
  const relatedCategory = website.category;
  const relatedName =
    relatedCategory && typeof relatedCategory === "object"
      ? relatedCategory.name
      : relatedCategory;
  const categoryId =
    website.categoryId ?? website.category_id ?? relatedCategory?.id;
  const mappedCategory = categoryById.value.get(String(categoryId));
  return String(
    mappedCategory?.name ||
      website.categoryName ||
      website.category_name ||
      relatedName ||
      "",
  ).trim();
}

function getWebsiteCategoryKey(website = {}) {
  return normalizeCategoryKey(getWebsiteCategoryName(website));
}

const allWebsites = computed(() => {
  const result = new Map();
  const addWebsite = (website, category) => {
    const normalizedWebsite = normalizeWebsite(website);
    const key = websiteKey(normalizedWebsite);
    if (!key || result.has(key)) return;
    const categoryName =
      getWebsiteCategoryName(website) || category?.name || "";
    result.set(key, {
      ...normalizedWebsite,
      category_id:
        normalizedWebsite.category_id ??
        normalizedWebsite.categoryId ??
        category?.id,
      category_name: categoryName || normalizedWebsite.category_name,
    });
  };

  props.categories.forEach((category) => {
    (props.categorySitesMap?.[category.id] || []).forEach((website) =>
      addWebsite(website, category),
    );
  });

  Object.values(props.categorySitesMap || {}).forEach((websites) => {
    normalizeList(websites).forEach((website) => addWebsite(website));
  });

  return [...result.values()];
});

const categoryOptions = computed(() => {
  const options = [
    { name: "全部", description: "浏览当前收录的全部网站资源。" },
  ];
  const seen = new Set(["全部"]);
  const addCategory = (category) => {
    const name = String(category?.name || category || "").trim();
    if (!name || seen.has(name)) return;
    seen.add(name);
    options.push({
      name,
      description: category?.description || "浏览该分类下收录的网站资源。",
    });
  };

  props.categories.forEach(addCategory);
  allWebsites.value.forEach((website) =>
    addCategory(getWebsiteCategoryName(website)),
  );
  return options;
});

const filteredWebsites = computed(() => {
  const list = Array.isArray(allWebsites.value) ? allWebsites.value : [];
  const categoryKey = normalizeCategoryKey(activeCategory.value);
  if (categoryKey === "all") return list;
  return list.filter(
    (website) => getWebsiteCategoryKey(website) === categoryKey,
  );
});

const visibleWebsiteCount = computed(() => filteredWebsites.value.length);
const normalizedVisibleLimit = computed(() => {
  const value = Number(visibleLimit.value);
  if (!Number.isFinite(value) || value < 1) return PAGE_SIZE;
  return Math.max(PAGE_SIZE, value);
});
const renderedWebsites = computed(() =>
  filteredWebsites.value.slice(0, normalizedVisibleLimit.value),
);
const activeCategoryDescription = computed(
  () =>
    categoryOptions.value.find(
      (category) => category.name === activeCategory.value,
    )?.description || "浏览当前分类下的网站资源。",
);
function normalizeList(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function categoryIcon(name) {
  return CATEGORY_ICON_MAP[String(name || "").trim()] || Folder;
}

function handleCategoryChange(categoryName) {
  activeCategory.value = categoryName;
  visibleLimit.value = PAGE_SIZE;
}

function loadMoreWebsites() {
  visibleLimit.value += PAGE_SIZE;
}
</script>

<style scoped>
.category-section {
  display: grid;
  gap: 24px;
  min-width: 0;
  padding: 0;
}

.category-heading {
  display: grid;
  gap: 10px;
}

.category-heading p {
  margin: 0 0 8px;
  color: var(--color-primary);
  font-weight: 850;
}

.category-heading h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(32px, 4vw, 46px);
  line-height: 1.12;
}

.category-heading > span {
  display: block;
  color: var(--color-text);
  line-height: 1.75;
}

.category-filter-bar {
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.68);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(18px);
}

.category-filter-bar {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 20px;
  border-radius: 22px;
  padding: 10px 12px;
}

.category-filter-bar__label {
  display: flex;
  min-width: 170px;
  align-items: center;
  gap: 10px;
  padding: 0 6px;
}

.category-filter-bar__icon {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 14px;
  background: var(--color-soft-orange);
  color: var(--color-primary);
}

.category-filter-bar__icon :deep(svg) {
  width: 20px;
  height: 20px;
}

.category-filter-bar__copy {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.category-filter-bar__copy strong {
  color: var(--color-heading);
  font-size: 15px;
}

.category-filter-bar__copy small {
  overflow: hidden;
  color: var(--color-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-nav {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding: 2px 0;
  scrollbar-width: thin;
}

.category-tab {
  display: inline-flex;
  min-height: 38px;
  flex: 0 0 auto;
  align-items: center;
  gap: 7px;
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  background: rgba(241, 245, 249, 0.74);
  color: #64748b;
  padding: 0 13px;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    color 180ms ease,
    background-color 180ms ease;
}

.category-tab :deep(svg) {
  width: 16px;
  height: 16px;
}

.category-tab:hover,
.category-tab:focus-visible {
  border-color: rgba(255, 112, 88, 0.28);
  background: rgba(255, 247, 244, 0.94);
  color: var(--color-primary);
  outline: none;
  transform: translateY(-1px);
}

.category-tab--active,
.category-tab--active:hover,
.category-tab--active:focus-visible {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #ffffff;
  box-shadow: 0 8px 20px rgba(255, 112, 88, 0.2);
}

.website-grid-state {
  min-width: 0;
}

.website-grid-toolbar {
  display: flex;
  min-height: 28px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.website-grid-toolbar p {
  margin: 0;
  color: var(--color-muted);
  font-size: 14px;
  font-weight: 750;
}

.website-card-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 20px;
  min-width: 0;
}

.website-card-grid :deep(.website-card--category) {
  height: 100%;
}

.website-load-more {
  display: block;
  margin: 22px auto 0;
  border: 1px solid rgba(255, 112, 88, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-primary);
  padding: 9px 20px;
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform 180ms ease,
    background-color 180ms ease,
    box-shadow 180ms ease;
}

.website-load-more:hover,
.website-load-more:focus-visible {
  background: rgba(255, 247, 244, 0.96);
  box-shadow: 0 8px 20px rgba(255, 112, 88, 0.12);
  outline: none;
  transform: translateY(-1px);
}

.website-skeleton-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 20px;
}

.website-skeleton-card {
  display: grid;
  min-height: 228px;
  align-content: start;
  gap: 16px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: #ffffff;
  padding: 22px;
}

.website-skeleton-card span,
.website-skeleton-card b,
.website-skeleton-card i {
  display: block;
  border-radius: 10px;
  background: linear-gradient(90deg, #f0f1f3 25%, #fafafa 50%, #f0f1f3 75%);
  background-size: 200% 100%;
  animation: website-skeleton 1.2s ease-in-out infinite;
}

.website-skeleton-card span {
  width: 48px;
  height: 48px;
}

.website-skeleton-card b {
  width: 58%;
  height: 20px;
}

.website-skeleton-card i {
  width: 100%;
  height: 50px;
}

@keyframes website-skeleton {
  to {
    background-position: -200% 0;
  }
}

.category-request-note {
  min-height: 38px;
  border: 1px solid var(--color-border-soft);
  border-radius: 12px;
  background: var(--color-soft);
  color: var(--color-muted);
  padding: 10px 12px;
  font-size: 13px;
}

.category-request-state {
  display: grid;
  min-height: 180px;
  place-items: center;
  align-content: center;
  gap: 12px;
  border: 1px dashed var(--color-border);
  border-radius: 22px;
  background: #ffffff;
  color: var(--color-text);
  padding: 28px;
  text-align: center;
}

.category-request-state--error {
  border-color: rgba(192, 57, 43, 0.28);
  background: #fffafa;
}

.category-request-state button {
  min-height: 40px;
  border: 1px solid var(--color-heading);
  border-radius: var(--radius-pill);
  background: var(--color-heading);
  color: #ffffff;
  padding: 0 16px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.category-request-state button:hover,
.category-request-state button:focus-visible {
  background: #000000;
  outline: 3px solid rgba(15, 23, 42, 0.18);
  outline-offset: 2px;
}

.category-empty-state {
  display: grid;
  min-height: 300px;
  place-items: center;
  align-content: center;
  gap: 10px;
  border: 1px dashed rgba(100, 116, 139, 0.24);
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.76);
  padding: 40px 24px;
  text-align: center;
}

.category-empty-state__icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 16px;
  background: var(--color-soft-orange);
  color: var(--color-primary);
  font-size: 24px;
}

.category-empty-state h3 {
  margin: 0;
  color: var(--color-heading);
  font-size: 20px;
}

.category-empty-state p {
  margin: 0;
  color: var(--color-muted);
  line-height: 1.7;
}

@media (max-width: 1200px) {
  .website-card-grid,
  .website-skeleton-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .category-filter-bar {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
  }

  .category-filter-bar__label {
    min-width: 0;
  }

  .category-nav {
    width: 100%;
  }

  .website-card-grid,
  .website-skeleton-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .website-card-grid,
  .website-skeleton-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 480px) {
  .website-card-grid,
  .website-skeleton-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  .website-skeleton-card span,
  .website-skeleton-card b,
  .website-skeleton-card i,
  .category-tab {
    animation: none;
    transition: none;
  }
}
</style>
