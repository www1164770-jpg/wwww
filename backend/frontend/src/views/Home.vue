<template>
  <div class="page">
    <AppHeader />

    <main class="home-main">
      <HeroSearch v-model="keyword" @search="goSearch(keyword)" />
      <ToolMarquee :sites="marqueeSites" @visit="visitSite" />

      <div v-if="loading || error" class="home-state">
        <LoadingState v-if="loading" />
        <EmptyState v-else title="首页数据加载失败" :description="error" />
      </div>

      <template v-else>
        <section id="categories" class="home-anchor-section">
          <CategorySection :categories="categories" />
        </section>

        <section id="career" class="home-anchor-section">
          <CareerRecommend @select-career="goSearch" />
        </section>

        <section id="recommend" class="home-anchor-section">
          <RecommendSection
            :sites="recommended"
            :logged-in="loggedIn"
            :favorite-pending-ids="favoritePendingIds"
            @favorite="toggleFavorite"
            @visit="visitSite"
          />
        </section>

        <section id="hot" class="home-anchor-section">
          <HotSitesSection
            :sites="hotSites"
            :favorite-pending-ids="favoritePendingIds"
            :refreshing="hotRefreshing"
            :error="hotError"
            @favorite="toggleFavorite"
            @visit="visitSite"
            @refresh="refreshHotSites"
          />
        </section>

        <section id="latest" class="home-anchor-section">
          <LatestSitesSection
            :sites="latestSites"
            :favorite-pending-ids="favoritePendingIds"
            @favorite="toggleFavorite"
            @visit="visitSite"
          />
        </section>

        <section id="favorite-stack">
          <FavoriteStack :sites="hotSites" @visit="visitSite" />
        </section>
      </template>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import CareerRecommend from "../components/home/CareerRecommend.vue";
import CategorySection from "../components/home/CategorySection.vue";
import FavoriteStack from "../components/home/FavoriteStack.vue";
import HeroSearch from "../components/home/HeroSearch.vue";
import HotSitesSection from "../components/home/HotSitesSection.vue";
import LatestSitesSection from "../components/home/LatestSitesSection.vue";
import RecommendSection from "../components/home/RecommendSection.vue";
import ToolMarquee from "../components/home/ToolMarquee.vue";
import AppFooter from "../components/layout/AppFooter.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import { categoryAPI, favoriteAPI, siteAPI, unwrapList } from "../utils/api";
import { errorToast, successToast } from "../utils/toast";

const router = useRouter();
const keyword = ref("");
const categories = ref([]);
const recommended = ref([]);
const hotSites = ref([]);
const marqueeSites = ref([]);
const latestSites = ref([]);
const loading = ref(false);
const error = ref("");
const hotRefreshing = ref(false);
const hotError = ref("");
const favoritePendingIds = ref([]);
const loggedIn = computed(() => Boolean(localStorage.getItem("access_token")));

const aiKeywords = [
  "AI",
  "人工智能",
  "ChatGPT",
  "Claude",
  "Gemini",
  "AIGC",
  "生成式",
  "智能",
  "模型",
  "写作",
  "绘图",
  "编程",
  "设计",
  "效率",
  "开发",
  "学习",
  "文档",
];

const blockedKeywords = [
  "王者荣耀",
  "和平精英",
  "抖音",
  "快手",
  "游戏",
  "手游",
  "短视频",
];
const blockedNames = ["百度"];

function getSettledData(result, fallback = []) {
  if (result.status !== "fulfilled") return fallback;
  return unwrapList(result.value);
}

function normalizeList(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function normalizeUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  return `https://${url}`;
}

function isLikelyAiResource(site) {
  const text = [
    site.name,
    site.summary,
    site.description,
    site.category_name,
    ...(Array.isArray(site.tags) ? site.tags : []),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (
    blockedNames.some(
      (keyword) =>
        keyword.toLowerCase() === String(site.name || "").toLowerCase(),
    )
  ) {
    return false;
  }

  if (blockedKeywords.some((keyword) => text.includes(keyword.toLowerCase()))) {
    return false;
  }

  return aiKeywords.some((keyword) => text.includes(keyword.toLowerCase()));
}

function filterAiResources(sites) {
  return normalizeList(sites).filter(isLikelyAiResource);
}

function goSearch(value) {
  router.push({ path: "/search", query: { q: value || "" } });
}

async function visitSite(site) {
  const url = normalizeUrl(site?.url);
  if (url) {
    window.open(url, "_blank", "noopener,noreferrer");
  } else if (site?.id) {
    router.push(`/site/${site.id}`);
  }
  try {
    if (site?.id) {
      await siteAPI.recordClick(site.id);
    }
  } catch {
    // click logging should not block navigation
  }
}

async function toggleFavorite(site) {
  if (!loggedIn.value) {
    router.push({ path: "/login", query: { redirect: "/" } });
    return;
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

async function loadHotAiSites({
  excludeCurrent = false,
  preserveOnError = false,
} = {}) {
  hotError.value = "";
  const excludeIds = excludeCurrent
    ? hotSites.value
        .map((site) => site.id)
        .filter(Boolean)
        .join(",")
    : "";
  try {
    const randomRes = await siteAPI.getRandom({
      limit: 8,
      category: "AI工具",
      scene: "homepage",
      exclude_ids: excludeIds,
    });
    const randomSites = filterAiResources(unwrapList(randomRes));
    if (randomSites.length || !preserveOnError) {
      hotSites.value = randomSites;
    }
    if (randomSites.length) return randomSites;
  } catch {
    // fall through to hot AI resources
  }

  try {
    const hotRes = await siteAPI.getHot({ limit: 8, ai_only: 1 });
    const hotAiSites = filterAiResources(unwrapList(hotRes));
    if (hotAiSites.length || !preserveOnError) {
      hotSites.value = hotAiSites;
    }
    return hotAiSites;
  } catch {
    hotError.value = "AI 资源更新失败，请稍后重试";
    if (!preserveOnError) {
      hotSites.value = [];
    }
    throw new Error(hotError.value);
  }
}

async function refreshHotSites() {
  if (hotRefreshing.value) return;
  hotRefreshing.value = true;
  try {
    await loadHotAiSites({ excludeCurrent: true, preserveOnError: true });
  } catch {
    errorToast(hotError.value || "AI 资源更新失败，请稍后重试");
  } finally {
    hotRefreshing.value = false;
  }
}

async function loadMarqueeSites() {
  try {
    const response = await siteAPI.getRandom({
      limit: 16,
      category: "AI工具",
      scene: "marquee",
    });
    marqueeSites.value = filterAiResources(unwrapList(response));
  } catch {
    marqueeSites.value = [];
  }
}

async function loadHome() {
  loading.value = true;
  error.value = "";
  try {
    const [categoryRes, recommendRes, latestRes, hotRes] =
      await Promise.allSettled([
        categoryAPI.getCategories(),
        siteAPI.getRecommend({ limit: 8 }),
        siteAPI.getLatest({ limit: 8 }),
        loadHotAiSites(),
        loadMarqueeSites(),
      ]);

    const categoryData = getSettledData(categoryRes, []);
    const latestData = getSettledData(latestRes, []);
    const recommendData = getSettledData(recommendRes, []);

    categories.value = categoryData
      .filter((item) => !item.parent_id)
      .slice(0, 8);
    latestSites.value = normalizeList(latestData);
    const normalizedRecommend = normalizeList(recommendData);
    recommended.value = normalizedRecommend.length
      ? normalizedRecommend
      : hotSites.value;

    if (
      !recommended.value.length &&
      !hotSites.value.length &&
      !latestSites.value.length
    ) {
      error.value =
        hotRes.status === "rejected"
          ? hotError.value
          : "暂无网站数据，请检查后端接口或数据库演示数据";
      errorToast(error.value);
    } else {
      error.value = "";
    }
  } catch {
    error.value = "暂无网站数据，请检查后端接口或数据库演示数据";
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}

onMounted(loadHome);
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #ffffff 0%, #ffffff 45%, #fffaf8 100%);
}

.home-main {
  display: grid;
  gap: 0;
}

.home-state {
  width: min(var(--container), calc(100% - 40px));
  margin: 80px auto;
}

@media (max-width: 768px) {
  .home-state {
    width: min(100% - 28px, var(--container));
    margin: 56px auto;
  }
}
</style>
