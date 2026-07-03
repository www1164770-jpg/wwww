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
        <section id="categories" class="home-anchor-section reveal-on-scroll">
          <CategorySection :categories="categories" />
        </section>

        <section id="career" class="home-anchor-section reveal-on-scroll">
          <CareerRecommend
            :active-career="selectedCareer?.key || ''"
            @select-career="handleSelectCareer"
          />
        </section>

        <section
          v-if="selectedCareer"
          id="career-sites"
          class="home-anchor-section career-sites-section reveal-on-scroll"
        >
          <div class="section-heading">
            <span class="eyebrow">职业推荐</span>
            <h2>适合「{{ selectedCareer.name }}」的 AI 网站</h2>
            <p>根据职业场景、兴趣方向和网站质量为你推荐。</p>
          </div>

          <LoadingState
            v-if="careerLoading"
            text="正在匹配适合该职业的网站..."
          />

          <EmptyState
            v-else-if="careerError || !careerSites.length"
            title="暂无适合该职业的 AI 网站"
            description="可以先在后台添加该职业相关的网站资源"
          />

          <div v-else class="site-grid">
            <SiteCard
              v-for="site in careerSites"
              :key="site.id || site.url || site.name"
              :site="site"
              :favorited="Boolean(site.is_favorited)"
              :favorite-pending="favoritePendingIds.includes(site.id)"
              @favorite="toggleFavorite"
              @visit="visitSite"
            />
          </div>
        </section>

        <section id="recommend" class="home-anchor-section reveal-on-scroll">
          <RecommendSection
            :sites="recommended"
            :logged-in="loggedIn"
            :favorite-pending-ids="favoritePendingIds"
            @favorite="toggleFavorite"
            @visit="visitSite"
          />
        </section>

        <section id="hot" class="home-anchor-section reveal-on-scroll">
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

        <section id="latest" class="home-anchor-section reveal-on-scroll">
          <LatestSitesSection
            :sites="latestSites"
            :favorite-pending-ids="favoritePendingIds"
            @favorite="toggleFavorite"
            @visit="visitSite"
          />
        </section>

        <section
          id="favorite-stack"
          class="home-anchor-section reveal-on-scroll"
        >
          <FavoriteStack :sites="favoriteStackSites" @visit="visitSite" />
        </section>
      </template>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
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
import SiteCard from "../components/site/SiteCard.vue";
import { categoryAPI, favoriteAPI, siteAPI, unwrapList } from "../utils/api";
import { errorToast, successToast } from "../utils/toast";

const router = useRouter();
const keyword = ref("");
const categories = ref([]);
const recommended = ref([]);
const hotSites = ref([]);
const marqueeSites = ref([]);
const favoriteStackSites = ref([]);
const latestSites = ref([]);
const loading = ref(false);
const error = ref("");
const hotRefreshing = ref(false);
const hotError = ref("");
const selectedCareer = ref(null);
const careerSites = ref([]);
const careerLoading = ref(false);
const careerError = ref("");
const lastCareerSiteIds = ref([]);
const favoritePendingIds = ref([]);
const loggedIn = computed(() => Boolean(localStorage.getItem("access_token")));
let revealObserver = null;

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
  "代码",
  "前端",
  "后端",
  "数据分析",
  "可视化",
  "产品",
  "原型",
  "流程图",
  "UI",
  "UX",
  "教学",
  "课件",
  "办公",
  "GitHub",
  "MDN",
  "Vue",
  "React",
  "JavaScript",
  "Python",
  "Flask",
  "SQL",
  "Figma",
  "Canva",
  "Notion",
  "ProcessOn",
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

const fallbackPopularSites = [
  {
    id: "fallback-chatgpt",
    name: "ChatGPT",
    url: "https://chatgpt.com",
    category_name: "AI",
    external_only: true,
  },
  {
    id: "fallback-claude",
    name: "Claude",
    url: "https://claude.ai",
    category_name: "AI",
    external_only: true,
  },
  {
    id: "fallback-gemini",
    name: "Gemini",
    url: "https://gemini.google.com",
    category_name: "AI",
    external_only: true,
  },
  {
    id: "fallback-perplexity",
    name: "Perplexity",
    url: "https://www.perplexity.ai",
    category_name: "AI 搜索",
    external_only: true,
  },
  {
    id: "fallback-github",
    name: "GitHub",
    url: "https://github.com",
    category_name: "开发工具",
    external_only: true,
  },
  {
    id: "fallback-mdn",
    name: "MDN Web Docs",
    url: "https://developer.mozilla.org",
    category_name: "开发文档",
    external_only: true,
  },
  {
    id: "fallback-vue",
    name: "Vue 官方文档",
    url: "https://cn.vuejs.org",
    category_name: "开发文档",
    external_only: true,
  },
  {
    id: "fallback-flask",
    name: "Flask 官方文档",
    url: "https://flask.palletsprojects.com",
    category_name: "开发文档",
    external_only: true,
  },
  {
    id: "fallback-leetcode",
    name: "LeetCode",
    url: "https://leetcode.cn",
    category_name: "学习成长",
    external_only: true,
  },
  {
    id: "fallback-figma",
    name: "Figma",
    url: "https://www.figma.com",
    category_name: "设计资源",
    external_only: true,
  },
  {
    id: "fallback-canva",
    name: "Canva",
    url: "https://www.canva.com",
    category_name: "设计资源",
    external_only: true,
  },
  {
    id: "fallback-iconfont",
    name: "Iconfont",
    url: "https://www.iconfont.cn",
    category_name: "图标",
    external_only: true,
  },
  {
    id: "fallback-notion",
    name: "Notion",
    url: "https://www.notion.so",
    category_name: "效率办公",
    external_only: true,
  },
  {
    id: "fallback-feishu",
    name: "飞书",
    url: "https://www.feishu.cn",
    category_name: "效率办公",
    external_only: true,
  },
  {
    id: "fallback-processon",
    name: "ProcessOn",
    url: "https://www.processon.com",
    category_name: "流程图",
    external_only: true,
  },
].sort(() => Math.random() - 0.5);

const careerFallbackSites = {
  学生: ["ChatGPT", "Perplexity", "Notion", "ProcessOn"],
  前端开发: ["GitHub", "MDN Web Docs", "Vue 官方文档", "ChatGPT"],
  后端开发: ["GitHub", "Flask 官方文档", "LeetCode", "ChatGPT"],
  产品经理: ["Notion", "ProcessOn", "飞书", "Figma", "ChatGPT"],
  "UI/UX 设计师": ["Figma", "Canva", "Iconfont"],
  运营: ["ChatGPT", "Canva", "Notion", "飞书"],
  教师: ["ChatGPT", "Canva", "ProcessOn"],
  自媒体创作者: ["ChatGPT", "Canva"],
  数据分析师: ["ChatGPT"],
  其他: ["ChatGPT", "Claude", "Gemini", "Notion"],
};

function getSettledData(result, fallback = []) {
  if (result.status !== "fulfilled") return fallback;
  if (Array.isArray(result.value)) return result.value;
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

function getSiteKey(site) {
  return site?.id || site?.url || site?.name;
}

function dedupeSites(list = [], usedKeys = new Set()) {
  const result = [];
  for (const site of normalizeList(list)) {
    const key = getSiteKey(site);
    if (!key || usedKeys.has(key)) continue;
    usedKeys.add(key);
    result.push(site);
  }
  return result;
}

function siteIds(sites = []) {
  return normalizeList(sites)
    .map((site) => site.id)
    .filter(Boolean);
}

function idsParam(ids = []) {
  return Array.from(new Set(ids.filter(Boolean))).join(",");
}

function fillWithFallback(sites, limit, usedKeys = new Set()) {
  const result = dedupeSites(
    [...normalizeList(sites), ...fallbackPopularSites],
    usedKeys,
  ).slice(0, limit);
  if (result.length >= limit) return result;

  const resultKeys = new Set(result.map(getSiteKey));
  const supplements = fallbackPopularSites
    .filter((site) => !resultKeys.has(getSiteKey(site)))
    .slice(0, limit - result.length);
  return [...result, ...supplements];
}

function fillCareerFallback(sites, career, limit) {
  const names =
    careerFallbackSites[career?.name] || careerFallbackSites["其他"];
  const careerPool = names
    .map((name) => fallbackPopularSites.find((site) => site.name === name))
    .filter(Boolean);
  return dedupeSites([...normalizeList(sites), ...careerPool], new Set()).slice(
    0,
    limit,
  );
}

function hasSameSiteIds(nextSites, previousIds) {
  const nextIds = siteIds(nextSites);
  if (!nextIds.length || nextIds.length !== previousIds.length) return false;
  return nextIds.every((id, index) => id === previousIds[index]);
}

function isLikelyAiResource(site) {
  const text = [
    site.name,
    site.summary,
    site.description,
    site.category_name,
    ...(Array.isArray(site.tags) ? site.tags : []),
    ...(Array.isArray(site.occupations) ? site.occupations : []),
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
    // Click logging should never block opening the website.
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

async function requestHotSites({
  excludeCurrent = false,
  preserveOnError = false,
  excludeIds = [],
  targetRef = hotSites,
} = {}) {
  hotError.value = "";
  const requestExcludeIds = excludeCurrent
    ? [...excludeIds, ...siteIds(targetRef.value)]
    : excludeIds;
  const exclude_ids = idsParam(requestExcludeIds);

  try {
    const hotRes = await siteAPI.getHot({
      limit: 8,
      ai_only: 1,
      exclude_ids,
    });
    const sites = filterAiResources(unwrapList(hotRes));
    if (sites.length || !preserveOnError) {
      targetRef.value = sites;
    }
    if (sites.length) return sites;
  } catch {
    // Fall through to the random resource pool.
  }

  try {
    const randomRes = await siteAPI.getRandom({
      limit: 8,
      category: "AI工具",
      scene: "homepage",
      exclude_ids,
    });
    const sites = filterAiResources(unwrapList(randomRes));
    if (sites.length || !preserveOnError) {
      targetRef.value = sites;
    }
    return sites;
  } catch {
    hotError.value = "AI 资源更新失败，请稍后重试";
    if (!preserveOnError) {
      targetRef.value = [];
    }
    throw new Error(hotError.value);
  }
}

async function refreshHotSites() {
  if (hotRefreshing.value) return;
  hotRefreshing.value = true;
  try {
    const preservedSections = [
      ...marqueeSites.value,
      ...favoriteStackSites.value,
      ...recommended.value,
      ...latestSites.value,
      ...careerSites.value,
    ];
    const sites = await requestHotSites({
      excludeCurrent: true,
      preserveOnError: true,
      excludeIds: siteIds(preservedSections),
    });
    const usedKeys = new Set(preservedSections.map(getSiteKey));
    hotSites.value = fillWithFallback(sites, 8, usedKeys);
  } catch {
    errorToast(hotError.value || "AI 资源更新失败，请稍后重试");
  } finally {
    hotRefreshing.value = false;
  }
}

async function loadCareerSites(career) {
  selectedCareer.value = career;
  careerSites.value = [];
  careerError.value = "";
  careerLoading.value = true;
  const exclude_ids = idsParam(
    siteIds([
      ...marqueeSites.value,
      ...hotSites.value,
      ...favoriteStackSites.value,
      ...recommended.value,
      ...latestSites.value,
      ...careerSites.value,
    ]),
  );

  try {
    const recommendRes = await siteAPI.getRecommend({
      occupation: career.name,
      limit: 8,
      ai_only: 1,
      exclude_ids,
    });
    let sites = filterAiResources(unwrapList(recommendRes));

    if (!sites.length || hasSameSiteIds(sites, lastCareerSiteIds.value)) {
      const randomRes = await siteAPI.getRandom({
        limit: 8,
        category: "AI工具",
        scene: "career",
        occupation: career.name,
        exclude_ids,
      });
      sites = filterAiResources(unwrapList(randomRes));
    }

    careerSites.value = fillCareerFallback(sites, career, 8);
    lastCareerSiteIds.value = siteIds(careerSites.value);
  } catch {
    careerError.value = "职业推荐加载失败，请稍后重试";
    careerSites.value = [];
  } finally {
    careerLoading.value = false;
  }
}

async function handleSelectCareer(career) {
  await loadCareerSites(career);
  await nextTick();
  observeRevealElements();
  const target = document.getElementById("career-sites");
  if (target) {
    const top = target.getBoundingClientRect().top + window.scrollY - 96;
    window.scrollTo({ top, behavior: "smooth" });
  }
}

async function loadMarqueeSites(excludeIds = []) {
  try {
    const response = await siteAPI.getRandom({
      limit: 16,
      category: "AI工具",
      scene: "marquee",
      exclude_ids: idsParam(excludeIds),
    });
    return filterAiResources(unwrapList(response));
  } catch {
    return [];
  }
}

async function loadHome() {
  loading.value = true;
  error.value = "";
  try {
    const usedKeys = new Set();
    const [categoryRes, marqueeRes] = await Promise.allSettled([
      categoryAPI.getCategories(),
      loadMarqueeSites(),
    ]);

    const categoryData = getSettledData(categoryRes, []);
    categories.value = categoryData
      .filter((item) => !item.parent_id)
      .slice(0, 8);

    marqueeSites.value = fillWithFallback(
      getSettledData(marqueeRes, []),
      16,
      usedKeys,
    );

    const [hotRes] = await Promise.allSettled([
      requestHotSites({ excludeIds: siteIds(marqueeSites.value) }),
    ]);
    hotSites.value = fillWithFallback(getSettledData(hotRes, []), 8, usedKeys);

    const [favoriteRes] = await Promise.allSettled([
      requestHotSites({
        excludeIds: siteIds([...marqueeSites.value, ...hotSites.value]),
        targetRef: favoriteStackSites,
      }),
    ]);
    favoriteStackSites.value = fillWithFallback(
      getSettledData(favoriteRes, []),
      6,
      usedKeys,
    );

    const excludeForRest = idsParam(
      siteIds([
        ...marqueeSites.value,
        ...hotSites.value,
        ...favoriteStackSites.value,
      ]),
    );
    const [recommendRes, latestRes] = await Promise.allSettled([
      siteAPI.getRecommend({ limit: 8, exclude_ids: excludeForRest }),
      siteAPI.getLatest({ limit: 12 }),
    ]);

    recommended.value = dedupeSites(
      filterAiResources(getSettledData(recommendRes, [])),
      usedKeys,
    ).slice(0, 8);
    if (!recommended.value.length) {
      recommended.value = fillWithFallback([], 8, usedKeys);
    }

    latestSites.value = dedupeSites(
      getSettledData(latestRes, []),
      usedKeys,
    ).slice(0, 8);

    if (
      !recommended.value.length &&
      !hotSites.value.length &&
      !latestSites.value.length
    ) {
      error.value =
        hotError.value || "暂无网站数据，请检查后端接口或数据库演示数据";
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

function observeRevealElements() {
  const elements = Array.from(document.querySelectorAll(".reveal-on-scroll"));
  const reduceMotion = window.matchMedia?.(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  if (reduceMotion || !("IntersectionObserver" in window)) {
    elements.forEach((element) => element.classList.add("is-visible"));
    return;
  }

  if (!revealObserver) {
    revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver?.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.14,
        rootMargin: "0px 0px -60px 0px",
      },
    );
  }

  elements.forEach((element, index) => {
    if (element.classList.contains("is-visible")) return;
    if (element.dataset.revealObserved === "1") return;
    element.style.setProperty(
      "--reveal-delay",
      `${Math.min(index * 45, 260)}ms`,
    );
    element.dataset.revealObserved = "1";
    revealObserver.observe(element);
  });
}

onMounted(async () => {
  await loadHome();
  await nextTick();
  observeRevealElements();
});

onBeforeUnmount(() => {
  revealObserver?.disconnect();
  revealObserver = null;
});
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

.career-sites-section {
  display: grid;
  gap: 28px;
  padding: 42px 0 38px;
}

.career-sites-section .section-heading {
  width: min(var(--container), calc(100% - 40px));
  margin: 0 auto;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  border-radius: var(--radius-pill);
  background: rgba(255, 112, 88, 0.1);
  color: #ff7058;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 850;
}

.site-grid {
  display: grid;
  width: min(var(--container), calc(100% - 40px));
  margin: 0 auto;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}

@media (max-width: 768px) {
  .home-state {
    width: min(100% - 28px, var(--container));
    margin: 56px auto;
  }
}

@media (max-width: 900px) {
  .site-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .career-sites-section .section-heading,
  .site-grid {
    width: min(100% - 28px, var(--container));
  }

  .site-grid {
    grid-template-columns: 1fr;
  }
}
</style>
