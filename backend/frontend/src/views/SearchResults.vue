<template>
  <div class="page">
    <AppHeader />
    <main class="search-page">
      <header class="search-page__header">
        <div class="search-page__heading">
          <p class="search-page__eyebrow">站内搜索</p>
          <AnimatedPageTitle>{{ heading }}</AnimatedPageTitle>
          <p v-if="payload" class="search-page__count">
            找到 {{ total }} 个相关网站
            <span v-if="payload.relaxed">，已为你放宽多关键词匹配</span>
          </p>
        </div>
        <SearchBar
          v-model="keyword"
          :navigate-on-submit="false"
          :submitting="loading || refreshing"
          @search="submitSearch"
        />
      </header>

      <section v-if="routeQuery" class="search-controls" aria-label="搜索筛选">
        <SearchFilterDropdown
          v-model="category"
          label="分类"
          :options="categoryOptions"
          @change="applyFilters"
        />
        <SearchFilterDropdown
          v-model="sort"
          label="排序"
          :options="sortOptions"
          @change="applyFilters"
        />
        <button
          v-if="category || sort !== 'relevance'"
          type="button"
          class="clear-filters"
          @click="clearFilters"
        >
          <RotateCcw aria-hidden="true" />
          清除筛选
        </button>
        <span v-if="refreshing" class="refreshing-status" aria-live="polite">
          <LoaderCircle aria-hidden="true" />
          正在更新
        </span>
      </section>

      <p v-if="staleWarning" class="stale-warning" role="status">
        {{ staleWarning }}，当前显示上次缓存结果。
        <button type="button" @click="retrySearch">重新搜索</button>
      </p>

      <p v-if="categoryError" class="category-warning" role="status">
        分类筛选暂时不可用，仍可继续搜索站内网站。
      </p>

      <section class="results-panel" aria-live="polite">
        <LoadingState v-if="loading && !payload" text="正在搜索站内网站..." />

        <div v-else-if="loadError && !payload" class="error-state">
          <SearchX aria-hidden="true" />
          <h2>搜索失败</h2>
          <p>{{ loadError }}</p>
          <button type="button" @click="retrySearch">
            <RefreshCw aria-hidden="true" />
            重新搜索
          </button>
        </div>

        <div v-else-if="!routeQuery" class="empty-state">
          <Search aria-hidden="true" />
          <h2>搜索站内网站</h2>
          <p>输入网站名称、功能、分类、标签或使用场景。</p>
        </div>

        <div v-else-if="payload && !sites.length" class="empty-state">
          <SearchX aria-hidden="true" />
          <h2>没有找到相关网站</h2>
          <p>换一个关键词，或尝试搜索网站功能、分类和使用场景。</p>
          <div class="empty-actions">
            <button type="button" @click="clearKeyword">清除关键词</button>
            <RouterLink to="/categories">查看全部分类</RouterLink>
            <RouterLink to="/#recommend-tools">查看热门推荐</RouterLink>
            <RouterLink to="/">询问知航AI</RouterLink>
          </div>
        </div>

        <template v-else-if="payload">
          <SiteList :sites="sites" hide-actions @visit="visit" />
          <nav
            v-if="pagination.totalPages > 1"
            class="pagination"
            aria-label="搜索结果分页"
          >
            <button
              type="button"
              :disabled="pagination.page <= 1"
              aria-label="上一页"
              @click="goToPage(pagination.page - 1)"
            >
              <ChevronLeft aria-hidden="true" />
            </button>
            <button
              v-for="pageNumber in pageNumbers"
              :key="pageNumber"
              type="button"
              :class="{ 'is-current': pageNumber === pagination.page }"
              :aria-current="
                pageNumber === pagination.page ? 'page' : undefined
              "
              @click="goToPage(pageNumber)"
            >
              {{ pageNumber }}
            </button>
            <button
              type="button"
              :disabled="!pagination.hasMore"
              aria-label="下一页"
              @click="goToPage(pagination.page + 1)"
            >
              <ChevronRight aria-hidden="true" />
            </button>
          </nav>
        </template>
      </section>
    </main>
    <AppFooter />
  </div>
</template>

<script setup>
import {
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Search,
  SearchX,
} from "lucide-vue-next";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AnimatedPageTitle from "../components/common/AnimatedPageTitle.vue";
import AppFooter from "../components/layout/AppFooter.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SearchBar from "../components/common/SearchBar.vue";
import SearchFilterDropdown from "../components/search/SearchFilterDropdown.vue";
import SiteList from "../components/site/SiteList.vue";
import { useSearchStore } from "../stores/search";
import { normalizeSearchError } from "../stores/search";
import { categoryAPI, unwrapResponse } from "../utils/api";
import { visitSite } from "../utils/siteVisit";

const route = useRoute();
const router = useRouter();
const searchStore = useSearchStore();
const keyword = ref("");
const category = ref("");
const sort = ref("relevance");
const categories = ref([]);
const categoryError = ref("");
const sortOptions = [
  { value: "relevance", label: "相关度" },
  { value: "recommend", label: "推荐程度" },
  { value: "latest", label: "最近更新" },
  { value: "name", label: "名称排序" },
];
const payload = ref(null);
const loading = ref(false);
const refreshing = ref(false);
const loadError = ref("");
const staleWarning = ref("");
let requestController = null;
let requestSequence = 0;
let loadedSignature = "";

const routeQuery = computed(() =>
  String(route.query.q || "")
    .trim()
    .replace(/\s+/g, " "),
);
const sites = computed(() => payload.value?.items || []);
const pagination = computed(
  () =>
    payload.value?.pagination || {
      page: 1,
      pageSize: 20,
      total: 0,
      totalPages: 0,
      hasMore: false,
    },
);
const total = computed(() => pagination.value.total);
const categoryOptions = computed(() => [
  { value: "", label: "全部分类" },
  ...categories.value.map((item) => ({
    value: item.code || item.id,
    label: item.name,
  })),
]);
const heading = computed(() =>
  routeQuery.value ? `搜索结果：${routeQuery.value}` : "搜索网站",
);
const pageNumbers = computed(() => {
  const current = pagination.value.page;
  const last = pagination.value.totalPages;
  const start = Math.max(1, Math.min(current - 2, last - 4));
  const end = Math.min(last, Math.max(current + 2, 5));
  return Array.from({ length: Math.max(end - start + 1, 0) }, (_, index) =>
    Number(start + index),
  );
});

function normalizedSort(value) {
  return ["relevance", "recommend", "latest", "name"].includes(value)
    ? value
    : "relevance";
}

function currentRouteState() {
  return {
    q: routeQuery.value,
    category: String(route.query.category || "").trim(),
    sort: normalizedSort(String(route.query.sort || "relevance")),
    page: Math.max(Number.parseInt(route.query.page, 10) || 1, 1),
    page_size: 20,
  };
}

function stateSignature(state) {
  return JSON.stringify([state.q, state.category, state.sort, state.page]);
}

async function loadFromRoute(options = {}) {
  const state = currentRouteState();
  keyword.value = state.q;
  category.value = state.category;
  sort.value = state.sort;
  loadError.value = "";
  staleWarning.value = "";

  if (!state.q) {
    requestController?.abort();
    payload.value = null;
    loadedSignature = "";
    loading.value = false;
    refreshing.value = false;
    return;
  }

  const signature = stateSignature(state);
  if (signature !== loadedSignature) payload.value = null;
  requestController?.abort();
  const controller = new AbortController();
  requestController = controller;
  const sequence = ++requestSequence;
  loading.value = !payload.value;
  refreshing.value = Boolean(payload.value);

  try {
    const result = await searchStore.search(state, {
      force: options.force,
      signal: controller.signal,
    });
    if (sequence !== requestSequence) return;
    payload.value = result.payload;
    loadedSignature = signature;
    staleWarning.value = result.staleError?.message || "";
  } catch (error) {
    if (sequence !== requestSequence || error?.code === "ERR_CANCELED") return;
    const normalized = error.searchError || normalizeSearchError(error);
    loadError.value = normalized.message;
  } finally {
    if (sequence === requestSequence) {
      loading.value = false;
      refreshing.value = false;
    }
  }
}

function routeFor(overrides = {}) {
  const state = { ...currentRouteState(), ...overrides };
  const query = { q: state.q };
  if (state.category) query.category = state.category;
  if (state.sort !== "relevance") query.sort = state.sort;
  if (state.page > 1) query.page = String(state.page);
  return { path: "/search", query };
}

function submitSearch(value) {
  const query = String(value || "")
    .trim()
    .replace(/\s+/g, " ");
  if (!query) return;
  void router.push(routeFor({ q: query, page: 1 }));
}

function applyFilters() {
  void router.push(
    routeFor({ category: category.value, sort: sort.value, page: 1 }),
  );
}

function clearFilters() {
  category.value = "";
  sort.value = "relevance";
  void router.push(routeFor({ category: "", sort: "relevance", page: 1 }));
}

function clearKeyword() {
  keyword.value = "";
  void router.push({ path: "/search" });
}

function retrySearch() {
  void loadFromRoute({ force: true });
}

function goToPage(page) {
  const nextPage = Math.max(1, Math.min(page, pagination.value.totalPages));
  if (nextPage === pagination.value.page) return;
  void router.push(routeFor({ page: nextPage }));
}

function visit(site) {
  visitSite(site, { source: "search" });
}

function flattenCategories(value) {
  const source = Array.isArray(value)
    ? value
    : value?.items || value?.categories || [];
  const result = new Map();
  const visit = (item) => {
    if (!item || result.has(item.id)) return;
    result.set(item.id, item);
    (item.children || []).forEach(visit);
  };
  source.forEach(visit);
  return [...result.values()];
}

watch(
  () => route.fullPath,
  () => void loadFromRoute(),
  { immediate: true },
);

onMounted(async () => {
  try {
    const response = await categoryAPI.getCategories();
    categories.value = flattenCategories(unwrapResponse(response));
    categoryError.value = "";
  } catch (error) {
    categories.value = [];
    categoryError.value =
      error?.response?.data?.message || "分类筛选暂时不可用";
  }
});

onBeforeUnmount(() => requestController?.abort());
</script>

<style scoped>
.page {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  background: var(--app-page-bg, transparent);
}

.search-page {
  display: grid;
  flex: 1 0 auto;
  width: min(1440px, calc(100% - 48px));
  min-width: 0;
  margin: 0 auto;
  padding: 42px 0 76px;
  color: var(--app-text-secondary);
  font-family:
    Inter,
    "PingFang SC",
    "Noto Sans SC",
    "Microsoft YaHei",
    sans-serif;
}

.search-page__header {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(520px, 820px);
  align-items: center;
  gap: 32px;
  padding: 26px 0 34px;
  border-bottom: 1px solid var(--color-border);
}

.search-page__heading {
  min-width: 0;
}

.search-page__eyebrow {
  margin: 0 0 8px;
  color: var(--color-primary-dark);
  font-size: 13px;
  font-weight: 850;
}

h1 {
  overflow-wrap: anywhere;
  margin: 0;
  color: var(--color-heading);
  font-size: 32px;
  line-height: 1.3;
  letter-spacing: 0;
}

.search-page__count {
  margin: 8px 0 0;
  color: var(--color-muted);
  line-height: 1.6;
}

.search-page__header :deep(.search-bar) {
  width: 100%;
}

.search-controls {
  display: flex;
  min-height: 86px;
  align-items: end;
  gap: 14px;
  padding: 18px 0;
  border-bottom: 1px solid var(--color-border);
}

.clear-filters,
.error-state button,
.empty-actions button,
.empty-actions a {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: #ffffff;
  color: #0f172a;
  padding: 0 14px;
  text-decoration: none;
  font-weight: 800;
}

.clear-filters svg,
.error-state button svg {
  width: 17px;
  height: 17px;
}

.clear-filters {
  min-height: 46px;
  border-color: rgba(255, 255, 255, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.055);
  color: rgba(255, 255, 255, 0.78);
  font-weight: 500;
  transition:
    border-color 180ms ease,
    background 180ms ease,
    color 180ms ease;
}

.clear-filters:hover,
.clear-filters:focus-visible {
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.09);
  color: #ffffff;
  outline: none;
}

.refreshing-status {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  color: var(--color-muted);
  font-size: 13px;
}

.refreshing-status svg {
  width: 17px;
  animation: page-spin 0.8s linear infinite;
}

.stale-warning {
  margin: 16px 0 0;
  border-left: 3px solid #d69e2e;
  background: #fffaf0;
  color: #744210;
  padding: 11px 14px;
  font-size: 14px;
}

.category-warning {
  margin: 16px 0 0;
  border-left: 3px solid rgba(255, 112, 88, 0.72);
  background: var(--app-panel-soft-bg);
  color: var(--app-text-secondary);
  padding: 11px 14px;
  font-size: 14px;
}

.stale-warning button {
  border: 0;
  background: transparent;
  color: #9c4221;
  font-weight: 850;
}

.results-panel {
  position: relative;
  min-width: 0;
  min-height: 220px;
  padding-top: 28px;
}

.results-panel :deep(.loading-state) {
  min-height: 220px;
  box-sizing: border-box;
  align-content: center;
  padding: 28px 24px;
}

.results-panel :deep(.site-list) {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.results-panel :deep(.site-card-reveal.reveal-on-scroll) {
  opacity: 1;
  transform: none;
  transition: none;
  will-change: auto;
}

.error-state,
.empty-state {
  display: grid;
  min-height: 330px;
  place-items: center;
  align-content: center;
  gap: 12px;
  border: 1px dashed var(--color-border);
  border-radius: 8px;
  padding: 36px 24px;
  text-align: center;
}

.error-state > svg,
.empty-state > svg {
  width: 42px;
  height: 42px;
  color: var(--color-primary);
}

.error-state h2,
.empty-state h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: 22px;
}

.error-state p,
.empty-state p {
  margin: 0;
  color: var(--color-muted);
  line-height: 1.7;
}

.error-state button {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #ffffff;
}

.empty-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 8px;
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-top: 30px;
}

.pagination button {
  display: inline-grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: #ffffff;
  color: #0f172a;
  font-weight: 800;
}

.pagination button.is-current {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #ffffff;
}

.pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.pagination svg {
  width: 18px;
}

@keyframes page-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1080px) {
  .search-page__header {
    grid-template-columns: 1fr;
  }

  .search-page__header :deep(.search-bar) {
    margin: 0;
  }

  .results-panel :deep(.site-list) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .search-page {
    width: min(100% - 28px, 1440px);
    padding-top: 24px;
  }

  .search-page__header {
    gap: 22px;
    padding-top: 12px;
  }

  h1 {
    font-size: 26px;
  }

  .search-controls {
    display: grid;
    grid-template-columns: 1fr 1fr;
    align-items: end;
  }

  .search-controls :deep(.filter-dropdown) {
    width: 100%;
  }

  .clear-filters {
    grid-column: 1 / -1;
  }

  .refreshing-status {
    grid-column: 1 / -1;
    margin-left: 0;
  }

  .results-panel :deep(.site-list) {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .refreshing-status svg {
    animation: none;
  }
}
</style>
