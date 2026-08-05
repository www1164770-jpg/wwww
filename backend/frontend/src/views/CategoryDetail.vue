<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="category-header">
        <div class="category-heading">
          <div>
            <span class="category-eyebrow">RESOURCE DIRECTORY</span>
            <h1>网站分类</h1>
            <p>从开发、设计、学习到效率工具，按分类浏览当前收录的网站资源。</p>
          </div>
          <span class="category-result-count" aria-live="polite">
            {{ filteredWebsites.length }} 个网站
          </span>
        </div>

        <nav class="category-nav" aria-label="网站分类">
          <button
            v-for="category in categoryOptions"
            :key="category.label"
            type="button"
            class="category-tab"
            :class="{
              'category-tab--active': activeCategory === category.label,
            }"
            :aria-pressed="activeCategory === category.label"
            @click="handleCategoryChange(category.label)"
          >
            <component :is="category.icon" aria-hidden="true" />
            <span>{{ category.label }}</span>
          </button>
        </nav>
      </section>

      <details class="secondary-filters">
        <summary>
          <span>更多筛选</span>
          <span v-if="hasActiveFilters()" class="secondary-filters__count">
            已应用 {{ activeFilterCount() }} 项
          </span>
        </summary>
        <SiteFilter
          :key="route.fullPath"
          v-model="filters"
          :categories="children"
          :tags="tags"
          @change="handleFilterChange"
        />
      </details>

      <section
        ref="resultsPanel"
        class="website-content"
        :aria-busy="loading ? 'true' : 'false'"
      >
        <LoadingState
          v-if="isInitialLoading && websites.length === 0"
          text="正在加载网站资源..."
        />
        <CategoryErrorState
          v-else-if="error && websites.length === 0"
          :message="error"
          :retrying="loading"
          @retry="loadSites"
        />
        <template v-else>
          <div
            v-if="isRefreshing || loading || error"
            class="category-request-note"
            role="status"
          >
            <span v-if="loading">正在更新网站资源…</span>
            <template v-else>
              <span>{{ error }}</span>
              <button type="button" @click="loadSites">重试</button>
            </template>
          </div>

          <Transition name="view-switch" mode="out-in">
            <div
              v-if="!selectedWebsite"
              key="website-grid"
              class="website-grid-state"
            >
              <div class="category-results-toolbar">
                <p class="result-count">
                  {{ activeCategory }}
                  <span v-if="hasActiveFilters()" class="active-filter-count">
                    · 已应用 {{ activeFilterCount() }} 项筛选
                  </span>
                </p>
                <button
                  v-if="hasActiveFilters()"
                  type="button"
                  class="clear-filters-button"
                  @click="clearFilters"
                >
                  清除全部筛选
                </button>
              </div>

              <div v-if="filteredWebsites.length" class="category-site-grid">
                <SiteCard
                  v-for="website in filteredWebsites"
                  :key="websiteKey(website)"
                  :site="website"
                  variant="category"
                  selectable
                  :selected="websiteKey(website) === selectedWebsiteId"
                  hide-actions
                  @select="handleWebsiteClick"
                />
              </div>

              <button
                v-if="hasMoreSites"
                type="button"
                class="category-load-more"
                :disabled="loadingMore"
                @click="loadMoreSites"
              >
                {{ loadingMore ? "正在加载..." : "加载更多网站" }}
              </button>

              <div v-else class="category-empty-state" role="status">
                <span class="category-empty-state__icon" aria-hidden="true"
                  >⌂</span
                >
                <h2>该分类暂无网站资源</h2>
                <p>可以切换其他分类，或稍后再来查看最新收录的网站。</p>
              </div>
            </div>

            <section
              v-else
              key="website-detail"
              class="website-detail-layout"
              aria-label="网站详情"
            >
              <aside class="website-detail-sidebar">
                <div class="detail-sidebar-heading">
                  <span>当前分类</span>
                  <h2>{{ activeCategory }}</h2>
                  <p>{{ activeCategoryDescription }}</p>
                </div>
                <div class="website-detail-list" role="list">
                  <button
                    v-for="website in filteredWebsites"
                    :key="`detail-${websiteKey(website)}`"
                    type="button"
                    class="website-detail-list-item"
                    :class="{
                      'website-detail-list-item--active':
                        websiteKey(website) === selectedWebsiteId,
                    }"
                    :aria-pressed="websiteKey(website) === selectedWebsiteId"
                    :aria-expanded="websiteKey(website) === selectedWebsiteId"
                    @click="handleWebsiteClick(website)"
                  >
                    <SiteLogo
                      :name="website.name"
                      :url="normalizeUrl(website.url)"
                      :logo="website.logo_url || website.logo"
                      size="md"
                      decorative
                    />
                    <span class="website-detail-list-item__copy">
                      <strong>{{ website.name || "未命名网站" }}</strong>
                      <small>{{ getWebsiteDescription(website) }}</small>
                    </span>
                  </button>
                </div>
              </aside>

              <article class="website-detail-card" aria-live="polite">
                <header class="website-detail-card__header">
                  <div class="website-detail-card__identity">
                    <SiteLogo
                      :name="selectedWebsite.name"
                      :url="selectedWebsiteUrl"
                      :logo="selectedWebsite.logo_url || selectedWebsite.logo"
                      size="lg"
                    />
                    <div>
                      <span class="website-detail-card__category">
                        {{ getWebsiteCategory(selectedWebsite) || "网站资源" }}
                      </span>
                      <h2>{{ selectedWebsite.name || "未命名网站" }}</h2>
                      <p v-if="selectedWebsiteShortDescription">
                        {{ selectedWebsiteShortDescription }}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    class="collapse-detail-button"
                    aria-label="收起网站详情"
                    title="再次点击可收起"
                    @click="collapseDetails"
                  >
                    <span>再次点击可收起</span>
                    <ChevronUp aria-hidden="true" />
                  </button>
                </header>

                <div v-if="selectedWebsiteUrl" class="website-detail-actions">
                  <a
                    class="website-visit-button"
                    :href="selectedWebsiteUrl"
                    target="_blank"
                    rel="noopener noreferrer"
                    @click="recordWebsiteVisit(selectedWebsite)"
                  >
                    访问网站
                    <span aria-hidden="true">↗</span>
                  </a>
                </div>

                <div class="website-detail-card__body">
                  <section
                    v-if="selectedWebsiteDescription"
                    class="detail-section"
                  >
                    <h3>详细介绍</h3>
                    <p>{{ selectedWebsiteDescription }}</p>
                  </section>

                  <section
                    v-if="selectedWebsiteFeatures.length"
                    class="detail-section"
                  >
                    <h3>主要功能</h3>
                    <div class="detail-chip-list">
                      <span
                        v-for="feature in selectedWebsiteFeatures"
                        :key="feature"
                      >
                        {{ feature }}
                      </span>
                    </div>
                  </section>

                  <dl
                    v-if="selectedWebsiteUrl || selectedWebsiteAudiences.length"
                    class="website-facts"
                  >
                    <div v-if="selectedWebsiteUrl">
                      <dt>官网地址</dt>
                      <dd>
                        <a
                          :href="selectedWebsiteUrl"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {{ selectedWebsiteUrl }}
                        </a>
                      </dd>
                    </div>
                    <div v-if="selectedWebsiteAudiences.length">
                      <dt>适用人群</dt>
                      <dd>{{ selectedWebsiteAudiences.join("、") }}</dd>
                    </div>
                  </dl>

                  <section
                    v-if="selectedWebsiteScreenshots.length"
                    class="detail-section detail-screenshots"
                  >
                    <h3>相关预览</h3>
                    <div class="screenshot-grid">
                      <figure
                        v-for="screenshot in selectedWebsiteScreenshots"
                        :key="screenshot"
                      >
                        <img
                          :src="screenshot"
                          :alt="`${selectedWebsite.name || '网站'}预览图`"
                          @error="hideBrokenScreenshot"
                        />
                      </figure>
                    </div>
                  </section>
                </div>
              </article>
            </section>
          </Transition>
        </template>
      </section>
    </main>
    <AppFooter />
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onActivated,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import {
  BookOpen,
  Bot,
  ChevronUp,
  Code2,
  GraduationCap,
  Layers,
  Palette,
  Users,
  Zap,
} from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";
import AppFooter from "../components/layout/AppFooter.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import CategoryErrorState from "../components/category/CategoryErrorState.vue";
import SiteFilter from "../components/site/SiteFilter.vue";
import SiteCard from "../components/site/SiteCard.vue";
import SiteLogo from "../components/site/SiteLogo.vue";
import {
  categoryAPI,
  getSiteDescription,
  normalizeWebsiteList,
  normalizeUrl,
  siteAPI,
  tagAPI,
  unwrapList,
} from "../utils/api";
import { errorToast } from "../utils/toast";

const route = useRoute();
const router = useRouter();

const categoryOptions = [
  { label: "全部", icon: Layers, description: "浏览当前收录的全部网站资源。" },
  {
    label: "开发文档",
    icon: BookOpen,
    description: "查阅框架、语言与平台的权威文档。",
  },
  {
    label: "AI 工具",
    icon: Bot,
    description: "发现对话、创作与智能协作工具。",
  },
  {
    label: "设计灵感",
    icon: Palette,
    description: "收集界面、视觉与创意设计灵感。",
  },
  {
    label: "学习资源",
    icon: GraduationCap,
    description: "探索课程、资料与知识学习平台。",
  },
  {
    label: "开发社区",
    icon: Users,
    description: "加入开发者问答、交流与开源社区。",
  },
  {
    label: "效率工具",
    icon: Zap,
    description: "提升整理、协作与日常工作效率。",
  },
];

const categoryAliases = {
  开发文档: ["开发文档", "编程开发", "开发工具", "框架文档"],
  "AI 工具": ["AI 工具", "AI工具", "AI", "AI 神器", "人工智能"],
  设计灵感: ["设计灵感", "设计资源", "设计工具", "原型设计", "灵感采集"],
  学习资源: ["学习资源", "学习成长", "学术研究", "教育"],
  开发社区: ["开发社区"],
  效率工具: ["效率工具", "效率办公", "实用工具", "办公效率"],
};

const categories = ref([]);
const tags = ref([]);
const websites = ref([]);
const activeCategory = ref("全部");
const selectedWebsiteId = ref(null);
const loading = ref(false);
const isInitialLoading = ref(false);
const isRefreshing = ref(false);
const hasLoadedSuccessfully = ref(false);
const hasMoreSites = ref(false);
const loadingMore = ref(false);
const currentPage = ref(1);
const error = ref("");
const resultsPanel = ref(null);
const filters = reactive({
  category_id: "",
  tag: "",
  is_free: "",
  region: "",
  sort: "recommend",
});
const DEFAULT_SORT = "recommend";
const FILTER_QUERY_KEYS = ["category_id", "tag", "is_free", "region", "sort"];
const PAGE_SIZE = 24;
let activeRequestController = null;
let requestSequence = 0;
let siteCardsObserver;
const sitesByFilterCache = new Map();

function siteCacheKey(source = {}) {
  return JSON.stringify(cleanFilters(source));
}

function readSessionSiteCache(key) {
  try {
    const value = sessionStorage.getItem(`zhihangyu:category-sites:${key}`);
    const parsed = value ? JSON.parse(value) : null;
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeSessionSiteCache(key, items) {
  try {
    sessionStorage.setItem(
      `zhihangyu:category-sites:${key}`,
      JSON.stringify(items),
    );
  } catch {
    // Storage quota or privacy mode must not block the category page.
  }
}

const children = computed(() =>
  categories.value.filter(
    (item) => String(item.parent_id) === String(route.params.id),
  ),
);
const categoryById = computed(() => {
  const result = new Map();
  categories.value.forEach((category) =>
    result.set(String(category.id), category),
  );
  return result;
});

function flattenCategories(value) {
  const source = Array.isArray(value) ? value : value?.items || value || [];
  const result = new Map();
  const visit = (item) => {
    if (!item || result.has(item.id)) return;
    result.set(item.id, item);
    (item.children || []).forEach(visit);
  };
  source.forEach(visit);
  return [...result.values()];
}

function normalizeList(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function normalizeArray(value) {
  if (Array.isArray(value)) {
    return value
      .map((item) =>
        typeof item === "string"
          ? item.trim()
          : item?.name || item?.label || item?.url || item?.src || "",
      )
      .filter(Boolean);
  }
  if (typeof value === "string") {
    return value
      .split(/[\n,，、|]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function normalizeCategoryName(value) {
  return String(value || "")
    .trim()
    .replace(/\s+/g, "")
    .toLowerCase();
}

function getWebsiteCategory(website = {}) {
  const relatedCategory = website.category;
  const categoryFromRelation =
    relatedCategory && typeof relatedCategory === "object"
      ? relatedCategory.name
      : relatedCategory;
  const categoryFromId = categoryById.value.get(
    String(website.category_id ?? website.categoryId),
  );
  return String(
    website.category_name || categoryFromRelation || categoryFromId?.name || "",
  ).trim();
}

function getWebsiteDescription(website = {}) {
  return getSiteDescription(website) || "暂未提供网站简介";
}

function getProvidedWebsiteDescription(website = {}) {
  return getSiteDescription(website);
}

function websiteKey(website = {}) {
  return String(website.id ?? website.url ?? website.name ?? "");
}

function matchesCategory(website, categoryLabel) {
  if (categoryLabel === "全部") return true;
  const category = normalizeCategoryName(getWebsiteCategory(website));
  const aliases = categoryAliases[categoryLabel] || [categoryLabel];
  return aliases.some((alias) => normalizeCategoryName(alias) === category);
}

const filteredWebsites = computed(() => {
  if (activeCategory.value === "全部") return websites.value;
  return websites.value.filter((website) =>
    matchesCategory(website, activeCategory.value),
  );
});

const selectedWebsite = computed(() =>
  filteredWebsites.value.find(
    (website) => websiteKey(website) === selectedWebsiteId.value,
  ),
);
const activeCategoryDescription = computed(
  () =>
    categoryOptions.find((category) => category.label === activeCategory.value)
      ?.description || "浏览当前分类下的网站资源。",
);
const selectedWebsiteUrl = computed(() =>
  normalizeUrl(selectedWebsite.value?.url),
);
const selectedWebsiteShortDescription = computed(() => {
  const website = selectedWebsite.value || {};
  return (
    website.shortDescription ||
    website.short_description ||
    website.slogan ||
    website.summary ||
    getProvidedWebsiteDescription(website)
  );
});
const selectedWebsiteDescription = computed(() => {
  const website = selectedWebsite.value || {};
  return (
    website.description ||
    website.long_description ||
    website.introduction ||
    website.summary ||
    getProvidedWebsiteDescription(website)
  );
});
const selectedWebsiteFeatures = computed(() => {
  const website = selectedWebsite.value || {};
  return normalizeArray(
    website.features || website.feature_tags || website.tags,
  );
});
const selectedWebsiteAudiences = computed(() => {
  const website = selectedWebsite.value || {};
  return normalizeArray(
    website.audiences || website.target_audience || website.occupations,
  );
});
const selectedWebsiteScreenshots = computed(() => {
  const website = selectedWebsite.value || {};
  return normalizeArray(
    website.screenshots || website.preview_images || website.images,
  );
});

function queryValue(value) {
  return Array.isArray(value) ? value[0] || "" : String(value || "");
}

function routeFilterQuery() {
  return {
    category_id: queryValue(route.query.category_id),
    tag: queryValue(route.query.tag),
    is_free: queryValue(route.query.is_free),
    region: queryValue(route.query.region),
    sort: queryValue(route.query.sort) || DEFAULT_SORT,
  };
}

function applyRouteFilters() {
  Object.assign(filters, routeFilterQuery());
}

function filtersHaveActiveValues(source = filters) {
  return Boolean(
    String(source.category_id || "").trim() ||
    String(source.tag || "").trim() ||
    String(source.is_free || "").trim() ||
    String(source.region || "").trim() ||
    source.sort !== DEFAULT_SORT,
  );
}

function hasActiveFilters() {
  return filtersHaveActiveValues(filters);
}

function activeFilterCount() {
  return (
    [filters.category_id, filters.tag, filters.is_free, filters.region].filter(
      (value) => String(value || "").trim(),
    ).length + (filters.sort !== DEFAULT_SORT ? 1 : 0)
  );
}

function cleanFilters(source = {}) {
  const params = {
    category_id: source.category_id,
    page: 1,
    page_size: PAGE_SIZE,
    limit: PAGE_SIZE,
    sort: source.sort || DEFAULT_SORT,
    tag: source.tag,
    is_free: source.is_free,
    region: source.region,
  };
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value != null),
  );
}

async function fetchAllSites(nextFilters, signal, page = 1) {
  const response = await siteAPI.getSites(
    { ...cleanFilters(nextFilters), page, page_size: PAGE_SIZE, limit: PAGE_SIZE },
    { signal },
  );
  const payload = response?.data?.data || response?.data || {};
  const pageItems = normalizeWebsiteList(response);
  const pagination = payload.pagination || {
    page,
    totalPages: Number(payload.totalPages || payload.total_pages || 0),
    hasMore: Boolean(payload.hasMore),
  };
  pageItems.pagination = pagination;
  return pageItems;
}

async function loadSites(nextFilters = filters) {
  activeRequestController?.abort();
  const controller = new AbortController();
  activeRequestController = controller;
  requestSequence += 1;
  const currentRequest = requestSequence;
  const cacheKey = siteCacheKey(nextFilters);
  const cachedWebsites = sitesByFilterCache.get(cacheKey) || readSessionSiteCache(cacheKey);
  if (cachedWebsites.length) {
    websites.value = cachedWebsites;
    sitesByFilterCache.set(cacheKey, cachedWebsites);
  }
  const hasCurrentData = websites.value.length > 0;
  loading.value = true;
  isInitialLoading.value = !hasCurrentData;
  isRefreshing.value = hasCurrentData;
  error.value = "";
  try {
    const nextWebsites = await fetchAllSites(nextFilters, controller.signal);
    if (currentRequest !== requestSequence) return;
    websites.value = nextWebsites;
    currentPage.value = 1;
    hasMoreSites.value = Boolean(
      nextWebsites.pagination?.hasMore ||
        Number(nextWebsites.pagination?.page || 1) <
          Number(nextWebsites.pagination?.totalPages || 0),
    );
    sitesByFilterCache.set(cacheKey, nextWebsites);
    writeSessionSiteCache(cacheKey, nextWebsites);
    hasLoadedSuccessfully.value = true;
  } catch (err) {
    if (currentRequest !== requestSequence || err?.code === "ERR_CANCELED")
      return;
    error.value = err.response?.data?.msg || "网站加载失败，请稍后重试";
    errorToast(error.value);
  } finally {
    if (currentRequest === requestSequence) {
      loading.value = false;
      isInitialLoading.value = false;
      isRefreshing.value = false;
    }
  }
}

async function loadMoreSites() {
  if (loadingMore.value || !hasMoreSites.value || !activeRequestController) return;
  loadingMore.value = true;
  try {
    const result = await fetchAllSites(
      filters,
      activeRequestController.signal,
    currentPage.value + 1,
    );
    const seen = new Set(websites.value.map(websiteKey));
    const nextItems = result.filter((item) => {
      const key = websiteKey(item);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    websites.value = [...websites.value, ...nextItems];
    currentPage.value += 1;
    hasMoreSites.value = Boolean(
      result.pagination?.hasMore ||
        currentPage.value < Number(result.pagination?.totalPages || 0),
    );
    sitesByFilterCache.set(siteCacheKey(filters), websites.value);
    writeSessionSiteCache(siteCacheKey(filters), websites.value);
  } catch (err) {
    if (err?.code !== "ERR_CANCELED") errorToast("加载更多网站失败，请稍后重试");
  } finally {
    loadingMore.value = false;
  }
}

async function syncFiltersToRoute() {
  const query = { ...route.query };
  FILTER_QUERY_KEYS.forEach((key) => delete query[key]);
  Object.entries(filters).forEach(([key, value]) => {
    if (FILTER_QUERY_KEYS.includes(key) && value && value !== DEFAULT_SORT) {
      query[key] = value;
    }
  });
  await router.replace({ name: route.name, params: route.params, query });
}

async function handleFilterChange(nextFilters) {
  Object.assign(filters, nextFilters || {});
  selectedWebsiteId.value = null;
  await syncFiltersToRoute();
}

async function clearFilters() {
  Object.assign(filters, {
    category_id: "",
    tag: "",
    is_free: "",
    region: "",
    sort: DEFAULT_SORT,
  });
  selectedWebsiteId.value = null;
  await syncFiltersToRoute();
}

function handleCategoryChange(categoryLabel) {
  activeCategory.value = categoryLabel;
  selectedWebsiteId.value = null;
}

function handleWebsiteClick(website) {
  const key = websiteKey(website);
  selectedWebsiteId.value = selectedWebsiteId.value === key ? null : key;
}

function collapseDetails() {
  selectedWebsiteId.value = null;
}

function hideBrokenScreenshot(event) {
  event.currentTarget.closest("figure")?.remove();
}

async function recordWebsiteVisit(website) {
  if (website?.id && !website.external_only) {
    await siteAPI.recordClick(website.id).catch(() => {});
  }
}

function observeSiteCards() {
  const elements = Array.from(
    resultsPanel.value?.querySelectorAll(".reveal-on-scroll") || [],
  );
  const reduceMotion = window.matchMedia?.(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  if (reduceMotion || !("IntersectionObserver" in window)) {
    elements.forEach((element) => element.classList.add("is-visible"));
    return;
  }

  siteCardsObserver?.disconnect();
  siteCardsObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        entry.target.classList.toggle("is-visible", entry.isIntersecting);
      });
    },
    { threshold: 0.16, rootMargin: "0px 0px -40px 0px" },
  );
  elements.forEach((element, index) => {
    element.style.setProperty(
      "--reveal-delay",
      `${Math.min(index * 35, 220)}ms`,
    );
    siteCardsObserver.observe(element);
  });
}

onMounted(async () => {
  applyRouteFilters();
  if (!filters.category_id && route.params.id) {
    filters.category_id = queryValue(route.params.id);
  }
  try {
    const [categoryRes, tagRes] = await Promise.all([
      categoryAPI.getCategories(),
      tagAPI.getTags(),
    ]);
    categories.value = flattenCategories(unwrapList(categoryRes));
    tags.value = unwrapList(tagRes);
  } catch (err) {
    error.value = err.response?.data?.msg || "筛选数据加载失败，请稍后重试";
    errorToast(error.value);
  }
  await loadSites();
});

onActivated(() => {
  if (!hasLoadedSuccessfully.value && !loading.value) {
    applyRouteFilters();
    void loadSites(filters);
  }
});

watch(
  () => [
    route.params.id,
    ...FILTER_QUERY_KEYS.map((key) => queryValue(route.query[key])),
  ],
  async () => {
    selectedWebsiteId.value = null;
    applyRouteFilters();
    await loadSites(filters);
  },
);

watch(
  filteredWebsites,
  async (items) => {
    if (
      selectedWebsiteId.value &&
      !items.some((website) => websiteKey(website) === selectedWebsiteId.value)
    ) {
      selectedWebsiteId.value = null;
    }
    await nextTick();
    observeSiteCards();
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  activeRequestController?.abort();
  requestSequence += 1;
  siteCardsObserver?.disconnect();
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background:
    radial-gradient(
      circle at 8% 10%,
      rgba(191, 245, 237, 0.2),
      transparent 28%
    ),
    #ffffff;
}

main {
  display: grid;
  gap: 24px;
  width: min(1200px, calc(100% - 40px));
  min-width: 0;
  margin: 44px auto 78px;
}

.category-header {
  display: grid;
  gap: 20px;
  min-width: 0;
}

.category-heading {
  display: flex;
  min-width: 0;
  align-items: end;
  justify-content: space-between;
  gap: 20px;
}

.category-eyebrow {
  display: inline-block;
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0.16em;
}

h1 {
  margin: 8px 0 0;
  color: var(--color-heading);
  font-size: clamp(36px, 5vw, 56px);
  line-height: 1.08;
}

.category-heading p {
  max-width: 700px;
  margin: 12px 0 0;
  color: #718096;
  line-height: 1.7;
}

.category-result-count {
  flex: 0 0 auto;
  border: 1px solid var(--color-border-soft);
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.7);
  color: var(--color-muted);
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 750;
}

.category-nav,
.secondary-filters,
.website-detail-sidebar,
.website-detail-card {
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(255, 255, 255, 0.68);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(18px);
}

.category-nav {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  border-radius: 22px;
  padding: 10px;
  scrollbar-width: thin;
}

.category-tab {
  display: inline-flex;
  min-height: 40px;
  flex: 0 0 auto;
  align-items: center;
  gap: 7px;
  border: 1px solid transparent;
  border-radius: var(--radius-pill);
  background: rgba(241, 245, 249, 0.74);
  color: #64748b;
  padding: 0 15px;
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

.category-tab--active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #ffffff;
  box-shadow: 0 8px 20px rgba(255, 112, 88, 0.2);
}

.category-tab--active:hover,
.category-tab--active:focus-visible {
  background: var(--color-primary-dark);
  color: #ffffff;
}

.secondary-filters {
  min-width: 0;
  border-radius: 18px;
  padding: 0 16px 16px;
}

.secondary-filters summary {
  display: flex;
  min-height: 48px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-heading);
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  list-style: none;
}

.secondary-filters summary::-webkit-details-marker {
  display: none;
}

.secondary-filters summary::after {
  content: "⌄";
  color: var(--color-muted);
  font-size: 18px;
  transition: transform 180ms ease;
}

.secondary-filters[open] summary::after {
  transform: rotate(180deg);
}

.secondary-filters__count {
  margin-left: auto;
  color: var(--color-primary);
  font-size: 12px;
}

.secondary-filters :deep(.site-filter) {
  border: 0;
  background: transparent;
  padding: 0;
  box-shadow: none;
}

.website-content {
  min-width: 0;
}

.category-request-note {
  display: flex;
  min-height: 38px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  border: 1px solid var(--color-border-soft);
  border-radius: 12px;
  background: var(--color-soft);
  color: var(--color-muted);
  padding: 8px 12px;
  font-size: 13px;
}

.category-request-note button,
.clear-filters-button {
  min-height: 36px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: #ffffff;
  color: var(--color-heading);
  padding: 0 13px;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.category-request-note button:hover,
.category-request-note button:focus-visible,
.clear-filters-button:hover,
.clear-filters-button:focus-visible {
  border-color: rgba(255, 112, 88, 0.42);
  color: var(--color-primary);
  outline: none;
}

.category-results-toolbar {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.result-count {
  margin: 0;
  color: var(--color-muted);
  font-size: 14px;
  font-weight: 750;
}

.active-filter-count {
  color: var(--color-heading);
  font-weight: 650;
}

.category-site-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 18px;
  min-width: 0;
}

.category-site-grid :deep(.website-card--category) {
  height: 100%;
}

.category-load-more {
  display: block;
  min-height: 42px;
  margin: 24px auto 0;
  border: 1px solid rgba(255, 112, 88, 0.28);
  border-radius: 10px;
  background: #fff7f3;
  color: var(--color-primary);
  padding: 0 22px;
  font-weight: 800;
  cursor: pointer;
}

.category-load-more:disabled {
  cursor: wait;
  opacity: 0.62;
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

.category-empty-state h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: 20px;
}

.category-empty-state p {
  margin: 0;
  color: var(--color-muted);
  line-height: 1.7;
}

.website-detail-layout {
  display: grid;
  grid-template-columns: minmax(250px, 30%) minmax(0, 1fr);
  gap: 22px;
  min-width: 0;
  align-items: start;
}

.website-detail-sidebar,
.website-detail-card {
  min-width: 0;
  border-radius: 22px;
}

.website-detail-sidebar {
  position: sticky;
  top: 92px;
  overflow: hidden;
}

.detail-sidebar-heading {
  display: grid;
  gap: 8px;
  border-bottom: 1px solid var(--color-border-soft);
  padding: 20px;
}

.detail-sidebar-heading > span {
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 850;
}

.detail-sidebar-heading h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: 22px;
}

.detail-sidebar-heading p {
  margin: 0;
  color: var(--color-muted);
  font-size: 13px;
  line-height: 1.65;
}

.website-detail-list {
  display: grid;
  max-height: 620px;
  gap: 6px;
  overflow-y: auto;
  padding: 10px;
}

.website-detail-list-item {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  border: 1px solid transparent;
  border-radius: 15px;
  background: transparent;
  color: inherit;
  padding: 10px;
  text-align: left;
  cursor: pointer;
  transition:
    background-color 180ms ease,
    border-color 180ms ease,
    transform 180ms ease;
}

.website-detail-list-item:hover,
.website-detail-list-item:focus-visible,
.website-detail-list-item--active {
  border-color: rgba(255, 112, 88, 0.34);
  background: rgba(255, 247, 244, 0.9);
  outline: none;
}

.website-detail-list-item:hover,
.website-detail-list-item:focus-visible {
  transform: translateY(-1px);
}

.website-detail-list-item--active {
  box-shadow: inset 3px 0 0 var(--color-primary);
}

.website-detail-list-item__copy {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.website-detail-list-item__copy strong,
.website-detail-list-item__copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.website-detail-list-item__copy strong {
  color: var(--color-heading);
  font-size: 14px;
}

.website-detail-list-item__copy small {
  color: var(--color-muted);
  font-size: 12px;
}

.website-detail-card {
  overflow: hidden;
}

.website-detail-card__header {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid var(--color-border-soft);
  padding: clamp(22px, 4vw, 34px);
}

.website-detail-card__identity {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 15px;
}

.website-detail-card__identity > div {
  min-width: 0;
}

.website-detail-card__category {
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 850;
}

.website-detail-card h2 {
  margin: 6px 0 5px;
  color: var(--color-heading);
  font-size: clamp(24px, 4vw, 34px);
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.website-detail-card__identity p {
  max-width: 620px;
  margin: 0;
  color: var(--color-muted);
  line-height: 1.65;
}

.collapse-detail-button {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.82);
  color: var(--color-muted);
  padding: 9px 12px;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  transition:
    border-color 180ms ease,
    color 180ms ease,
    transform 180ms ease;
}

.collapse-detail-button :deep(svg) {
  width: 16px;
  height: 16px;
}

.collapse-detail-button:hover,
.collapse-detail-button:focus-visible {
  border-color: rgba(255, 112, 88, 0.42);
  color: var(--color-primary);
  outline: none;
  transform: translateY(-1px);
}

.website-detail-actions {
  padding: 20px clamp(22px, 4vw, 34px) 0;
}

.website-visit-button {
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  gap: 8px;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 0 18px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 850;
  box-shadow: 0 10px 22px rgba(255, 112, 88, 0.18);
  transition:
    background-color 180ms ease,
    transform 180ms ease;
}

.website-visit-button:hover,
.website-visit-button:focus-visible {
  background: var(--color-primary-dark);
  color: #ffffff;
  outline: none;
  transform: translateY(-1px);
}

.website-detail-card__body {
  display: grid;
  gap: 26px;
  padding: clamp(22px, 4vw, 34px);
}

.detail-section {
  display: grid;
  gap: 10px;
}

.detail-section h3 {
  margin: 0;
  color: var(--color-heading);
  font-size: 17px;
}

.detail-section p {
  margin: 0;
  color: var(--color-text);
  line-height: 1.85;
  white-space: pre-line;
}

.detail-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-chip-list span {
  border-radius: var(--radius-pill);
  background: var(--color-soft-orange);
  color: var(--color-primary-dark);
  padding: 7px 11px;
  font-size: 13px;
  font-weight: 750;
}

.website-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}

.website-facts div {
  display: grid;
  gap: 7px;
  min-width: 0;
  border-radius: 15px;
  background: var(--color-soft);
  padding: 13px;
}

.website-facts dt {
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 800;
}

.website-facts dd {
  min-width: 0;
  margin: 0;
  color: var(--color-text);
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.website-facts a {
  color: var(--color-primary-dark);
  text-decoration: none;
}

.website-facts a:hover,
.website-facts a:focus-visible {
  text-decoration: underline;
  outline: none;
}

.screenshot-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.screenshot-grid figure {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--color-border-soft);
  border-radius: 15px;
  background: var(--color-soft);
}

.screenshot-grid img {
  display: block;
  width: 100%;
  max-height: 260px;
  object-fit: cover;
}

.view-switch-enter-active,
.view-switch-leave-active {
  transition:
    opacity 220ms ease,
    transform 220ms ease;
}

.view-switch-enter-from,
.view-switch-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 1100px) {
  .category-site-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .website-detail-layout {
    grid-template-columns: 1fr;
  }

  .website-detail-sidebar {
    position: static;
  }

  .website-detail-list {
    display: flex;
    max-height: none;
    overflow-x: auto;
  }

  .website-detail-list-item {
    min-width: 220px;
  }

  .category-site-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  main {
    width: min(100% - 28px, 1200px);
    margin-top: 32px;
  }

  .category-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .category-result-count {
    align-self: flex-start;
  }

  .category-site-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .website-detail-card__header {
    flex-direction: column;
  }

  .collapse-detail-button {
    align-self: flex-start;
  }
}

@media (max-width: 520px) {
  .category-results-toolbar,
  .category-request-note {
    align-items: stretch;
    flex-direction: column;
  }

  .clear-filters-button {
    width: 100%;
  }

  .category-site-grid,
  .website-facts,
  .screenshot-grid {
    grid-template-columns: 1fr;
  }

  .website-detail-card__identity {
    gap: 11px;
  }

  .website-detail-card__identity :deep(.site-logo--lg) {
    width: 42px;
    height: 42px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .category-tab,
  .website-detail-list-item,
  .collapse-detail-button,
  .website-visit-button,
  .view-switch-enter-active,
  .view-switch-leave-active {
    transition: none;
  }

  .category-tab:hover,
  .website-detail-list-item:hover,
  .website-detail-list-item:focus-visible,
  .collapse-detail-button:hover,
  .website-visit-button:hover {
    transform: none;
  }
}
</style>
