<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="category-hero">
        <h1>{{ currentCategory?.name || "分类详情" }}</h1>
        <p>
          {{
            currentCategory?.description ||
            "按标签、价格、地区和排序方式筛选该分类下的网站资源。"
          }}
        </p>
      </section>

      <div class="content-layout">
        <aside class="filter-panel">
          <h2>筛选条件</h2>
          <SiteFilter
            v-model="filters"
            :categories="children"
            :tags="tags"
            @change="loadSites"
          />
        </aside>

        <section ref="resultsPanel" class="results-panel">
          <LoadingState
            v-if="loading"
            text="正在加载该分类下的网站资源..."
          />
          <div v-else-if="error" class="category-results-state">
            <EmptyState
              title="分类网站加载失败，请稍后重试"
              :description="error"
            />
            <button type="button" class="retry-button" @click="loadSites">
              重新加载
            </button>
          </div>
          <div v-else-if="sites.length">
            <p class="result-count">共找到 {{ sites.length }} 个网站</p>
            <div class="category-site-grid">
              <SiteCard
                v-for="site in sites"
                :key="site.id || site.url || site.name"
                :site="site"
                :favorited="Boolean(site.is_favorited)"
                :favorite-pending="favoritePendingIds.includes(site.id)"
                @favorite="favorite"
                @visit="visit"
              />
            </div>
          </div>
          <EmptyState
            v-else
            title="当前分类下暂无匹配网站"
            description="请尝试切换筛选条件，或返回首页查看更多分类。"
          />
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import EmptyState from "../components/common/EmptyState.vue";
import SiteFilter from "../components/site/SiteFilter.vue";
import SiteCard from "../components/site/SiteCard.vue";
import {
  categoryAPI,
  favoriteAPI,
  normalizeUrl,
  siteAPI,
  tagAPI,
  unwrapList,
} from "../utils/api";
import { getAccessToken } from "../utils/auth";
import { errorToast, successToast } from "../utils/toast";

const route = useRoute();
const router = useRouter();
const categories = ref([]);
const tags = ref([]);
const sites = ref([]);
const loading = ref(false);
const error = ref("");
const favoritePendingIds = ref([]);
const resultsPanel = ref(null);
const filters = reactive({
  category_id: "",
  tag: "",
  is_free: "",
  region: "",
  sort: "recommend",
});
const currentCategory = computed(() =>
  categories.value.find((item) => String(item.id) === String(route.params.id)),
);
const children = computed(() =>
  categories.value.filter(
    (item) => String(item.parent_id) === String(route.params.id),
  ),
);

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

function cleanFilters(source = {}) {
  const params = {
    category_id: source.category_id || route.params.id,
    page: 1,
    page_size: 12,
    limit: 12,
    sort: source.sort || "recommend",
    tag: source.tag,
    is_free: source.is_free,
    region: source.region,
  };
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value != null),
  );
}

async function loadSites(nextFilters = filters) {
  loading.value = true;
  error.value = "";
  try {
    const response = await siteAPI.getSites(cleanFilters(nextFilters));
    sites.value = normalizeList(unwrapList(response));
  } catch (err) {
    error.value = err.response?.data?.msg || "网站加载失败，请稍后重试";
    sites.value = [];
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}

let siteCardsObserver;

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

  if (!siteCardsObserver) {
    siteCardsObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          entry.target.classList.toggle("is-visible", entry.isIntersecting);
        });
      },
      { threshold: 0.16, rootMargin: "0px 0px -40px 0px" },
    );
  }

  elements.forEach((element, index) => {
    element.style.setProperty(
      "--reveal-delay",
      `${Math.min(index * 35, 220)}ms`,
    );
    siteCardsObserver.observe(element);
  });
}
async function favorite(site) {
  if (!getAccessToken()) {
    return router.push({ path: "/login", query: { redirect: route.fullPath } });
  }
  if (favoritePendingIds.value.includes(site.id)) return;
  const wasFavorited = Boolean(site.is_favorited);
  favoritePendingIds.value = [...favoritePendingIds.value, site.id];
  try {
    if (wasFavorited) {
      await favoriteAPI.removeFavorite(site.id);
      site.is_favorited = false;
      successToast("已取消收藏");
    } else {
      await favoriteAPI.addFavorite(site.id);
      site.is_favorited = true;
      successToast("已收藏");
    }
  } catch {
    site.is_favorited = wasFavorited;
    errorToast("操作失败，请稍后重试");
  } finally {
    favoritePendingIds.value = favoritePendingIds.value.filter(
      (id) => id !== site.id,
    );
  }
}
async function visit(site) {
  const url = normalizeUrl(site?.url);
  if (site?.id && !site.external_only) {
    await siteAPI.recordClick(site.id).catch(() => {});
  }
  if (url) {
    window.open(url, "_blank", "noopener,noreferrer");
  } else if (site?.id && !site.external_only) {
    router.push(`/site/${site.id}`);
  }
}
onMounted(async () => {
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

watch(
  () => route.params.id,
  async () => {
    filters.category_id = "";
    await loadSites();
  },
);

watch(
  sites,
  async () => {
    await nextTick();
    observeSiteCards();
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  siteCardsObserver?.disconnect();
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #ffffff;
}

main {
  display: grid;
  gap: 26px;
  width: min(1180px, calc(100% - 40px));
  margin: 48px auto 78px;
}

.category-hero {
  display: grid;
  gap: 12px;
  border-radius: 24px;
  background:
    radial-gradient(
      circle at 12% 22%,
      rgba(191, 245, 237, 0.32),
      transparent 30%
    ),
    linear-gradient(135deg, #ffffff 0%, #fff4f1 100%);
  padding: clamp(34px, 5vw, 64px);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.04);
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(36px, 5vw, 56px);
}

.category-hero p {
  max-width: 720px;
  margin: 0;
  color: #718096;
  line-height: 1.7;
}

.content-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.filter-panel {
  position: sticky;
  top: 92px;
  display: grid;
  gap: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 20px;
  box-shadow: var(--shadow-soft);
}

.filter-panel h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: 20px;
}

.filter-panel :deep(.site-filter) {
  grid-template-columns: 1fr;
  border: 0;
  padding: 0;
  box-shadow: none;
}

.results-panel {
  min-width: 0;
}

.result-count {
  margin: 0 0 16px;
  color: var(--color-muted);
  font-size: 14px;
  font-weight: 750;
}

.category-results-state {
  display: grid;
  gap: 14px;
  justify-items: center;
}

.retry-button {
  min-height: 42px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 0 18px;
  font-weight: 800;
  cursor: pointer;
}

.retry-button:hover,
.retry-button:focus-visible {
  background: var(--color-primary-dark);
  outline: none;
}

.category-site-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(260px, 100%), 1fr));
  gap: 20px;
  min-width: 0;
}

@media (max-width: 920px) {
  .content-layout {
    grid-template-columns: 1fr;
  }

  .filter-panel {
    position: static;
  }
}

@media (max-width: 768px) {
  main {
    width: min(100% - 28px, 1180px);
    margin-top: 32px;
  }
}
</style>
