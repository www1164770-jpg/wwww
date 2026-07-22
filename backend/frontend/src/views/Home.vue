<template>
  <div class="page">
    <AppHeader />

    <main class="home-main">
      <HeroSearch v-model="keyword" @search="goSearch" />
      <ToolMarquee :sites="marqueeSites" @visit="visitSite" />

      <div v-if="loading || error" class="home-state">
        <LoadingState v-if="loading" />
        <EmptyState v-else title="首页数据加载失败" :description="error" />
      </div>

      <template v-else>
        <section id="categories" class="home-anchor-section reveal-on-scroll">
          <CategorySection
            :categories="categories"
            :category-sites-map="categorySitesMap"
            :loading-category-sites="loadingCategorySites"
            @visit-site="visitSite"
          />
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

          <div v-else>
            <div class="site-grid">
              <SiteCard
                v-for="site in careerSites"
                :key="site.id || site.url || site.name"
                :site="site"
                :show-reason="true"
                :favorited="Boolean(site.is_favorited)"
                :favorite-pending="favoritePendingIds.includes(site.id)"
                @favorite="toggleFavorite"
                @visit="visitSite"
              />
            </div>

            <div v-if="!loggedIn" class="ai-login-prompt">
              <div class="ai-login-prompt__content">
                <p class="ai-login-prompt__title">没有找到合适的网站？</p>
                <p class="ai-login-prompt__description">
                  登录后描述你的具体需求，AI 将为你推荐更适合的网站。
                </p>
              </div>
              <button
                type="button"
                class="ai-login-prompt__button"
                @click="goToAiAssistantLogin"
              >
                登录并使用 AI 助手
              </button>
            </div>
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

    <AiSiteAssistant v-if="loggedIn" @visit="visitSite" />
    <AppFooter />
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  onUpdated,
  ref,
} from "vue";
import { useRouter } from "vue-router";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import AiSiteAssistant from "../components/ai/AiSiteAssistant.vue";
import CareerRecommend from "../components/home/CareerRecommend.vue";
import CategorySection from "../components/home/CategorySection.vue";
import FavoriteStack from "../components/home/FavoriteStack.vue";
import HeroSearch from "../components/home/HeroSearch.vue";
import LatestSitesSection from "../components/home/LatestSitesSection.vue";
import RecommendSection from "../components/home/RecommendSection.vue";
import ToolMarquee from "../components/home/ToolMarquee.vue";
import AppFooter from "../components/layout/AppFooter.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import SiteCard from "../components/site/SiteCard.vue";
import {
  categoryAPI,
  favoriteAPI,
  getCategoryFallbackSites,
  normalizeUrl,
  siteAPI,
  unwrapList,
} from "../utils/api";
import { getAccessToken, isValidAuthToken } from "../utils/auth";
import { errorToast, successToast } from "../utils/toast";

const router = useRouter();
const keyword = ref("");
const categories = ref([]);
const categorySitesMap = ref({});
const loadingCategorySites = ref(false);
const recommended = ref([]);
const hotSites = ref([]);
const marqueeSites = ref([]);
const favoriteStackSites = ref([]);
const latestSites = ref([]);
const loading = ref(false);
const error = ref("");
const hotError = ref("");
const selectedCareer = ref(null);
const careerSites = ref([]);
const careerLoading = ref(false);
const careerError = ref("");
const lastCareerSiteIds = ref([]);
const favoritePendingIds = ref([]);
const loggedIn = computed(() => isValidAuthToken(getAccessToken()));
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
    id: "fallback-unsplash",
    name: "Unsplash",
    url: "https://unsplash.com",
    category_name: "设计资源",
    external_only: true,
  },
  {
    id: "fallback-stackoverflow",
    name: "Stack Overflow",
    url: "https://stackoverflow.com",
    category_name: "开发社区",
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
  {
    id: "fallback-trello",
    name: "Trello",
    url: "https://trello.com",
    category_name: "项目管理",
    external_only: true,
  },
  {
    id: "fallback-bilibili-learning",
    name: "Bilibili 学习区",
    url: "https://www.bilibili.com/v/knowledge",
    category_name: "学习成长",
    external_only: true,
  },
  {
    id: "fallback-coursera",
    name: "Coursera",
    url: "https://www.coursera.org",
    category_name: "学习成长",
    external_only: true,
  },
  {
    id: "fallback-dribbble",
    name: "Dribbble",
    url: "https://dribbble.com",
    category_name: "设计灵感",
    external_only: true,
  },
  {
    id: "fallback-kaggle",
    name: "Kaggle",
    url: "https://www.kaggle.com",
    category_name: "数据分析",
    external_only: true,
  },
  {
    id: "fallback-tableau",
    name: "Tableau",
    url: "https://www.tableau.com",
    category_name: "数据分析",
    external_only: true,
  },
  {
    id: "fallback-powerbi",
    name: "Power BI",
    url: "https://powerbi.microsoft.com",
    category_name: "数据分析",
    external_only: true,
  },
  {
    id: "fallback-jupyter",
    name: "Jupyter",
    url: "https://jupyter.org",
    category_name: "数据分析",
    external_only: true,
  },
].sort(() => Math.random() - 0.5);

const categoryFallbackSites = {
  AI工具: [
    {
      id: "fallback-ai-chatgpt",
      name: "ChatGPT",
      url: "https://chatgpt.com",
      summary: "OpenAI 的 AI 对话与效率工具。",
      category_name: "AI工具",
      external_only: true,
    },
    {
      id: "fallback-ai-claude",
      name: "Claude",
      url: "https://claude.ai",
      summary: "适合长文档处理、编程辅助和知识工作。",
      category_name: "AI工具",
      external_only: true,
    },
    {
      id: "fallback-ai-gemini",
      name: "Gemini",
      url: "https://gemini.google.com",
      summary: "Google 的多模态 AI 助手。",
      category_name: "AI工具",
      external_only: true,
    },
    {
      id: "fallback-ai-perplexity",
      name: "Perplexity",
      url: "https://www.perplexity.ai",
      summary: "面向资料检索和问答的 AI 搜索工具。",
      category_name: "AI工具",
      external_only: true,
    },
  ],
  编程开发: [
    {
      id: "fallback-dev-github",
      name: "GitHub",
      url: "https://github.com",
      summary: "代码托管与协作开发平台。",
      category_name: "编程开发",
      external_only: true,
    },
    {
      id: "fallback-dev-mdn",
      name: "MDN Web Docs",
      url: "https://developer.mozilla.org",
      summary: "权威 Web 开发文档。",
      category_name: "编程开发",
      external_only: true,
    },
    {
      id: "fallback-dev-vue",
      name: "Vue 官方文档",
      url: "https://vuejs.org",
      summary: "Vue.js 官方文档与最佳实践。",
      category_name: "编程开发",
      external_only: true,
    },
    {
      id: "fallback-dev-leetcode",
      name: "LeetCode",
      url: "https://leetcode.cn",
      summary: "算法练习和面试准备平台。",
      category_name: "编程开发",
      external_only: true,
    },
  ],
  设计资源: [
    {
      id: "fallback-design-figma",
      name: "Figma",
      url: "https://www.figma.com",
      summary: "在线协作设计和原型工具。",
      category_name: "设计资源",
      external_only: true,
    },
    {
      id: "fallback-design-canva",
      name: "Canva",
      url: "https://www.canva.com",
      summary: "在线设计与内容创作工具。",
      category_name: "设计资源",
      external_only: true,
    },
    {
      id: "fallback-design-iconfont",
      name: "Iconfont",
      url: "https://www.iconfont.cn",
      summary: "阿里巴巴矢量图标库。",
      category_name: "设计资源",
      external_only: true,
    },
    {
      id: "fallback-design-unsplash",
      name: "Unsplash",
      url: "https://unsplash.com",
      summary: "高质量免费图片素材站。",
      category_name: "设计资源",
      external_only: true,
    },
  ],
  效率办公: [
    {
      id: "fallback-office-notion",
      name: "Notion",
      url: "https://www.notion.so",
      summary: "笔记、知识库和项目管理工具。",
      category_name: "效率办公",
      external_only: true,
    },
    {
      id: "fallback-office-feishu",
      name: "飞书",
      url: "https://www.feishu.cn",
      summary: "团队协作、文档和项目沟通平台。",
      category_name: "效率办公",
      external_only: true,
    },
    {
      id: "fallback-office-processon",
      name: "ProcessOn",
      url: "https://www.processon.com",
      summary: "在线流程图和思维导图工具。",
      category_name: "效率办公",
      external_only: true,
    },
    {
      id: "fallback-office-trello",
      name: "Trello",
      url: "https://trello.com",
      summary: "轻量看板式项目管理工具。",
      category_name: "效率办公",
      external_only: true,
    },
  ],
  学习成长: [
    {
      id: "fallback-learn-bilibili",
      name: "Bilibili 学习区",
      url: "https://www.bilibili.com",
      summary: "覆盖课程、技能和知识内容的视频学习区。",
      category_name: "学习成长",
      external_only: true,
    },
    {
      id: "fallback-learn-coursera",
      name: "Coursera",
      url: "https://www.coursera.org",
      summary: "国际在线课程与职业证书平台。",
      category_name: "学习成长",
      external_only: true,
    },
    {
      id: "fallback-learn-khan",
      name: "Khan Academy",
      url: "https://www.khanacademy.org",
      summary: "免费的基础学科与通识学习平台。",
      category_name: "学习成长",
      external_only: true,
    },
    {
      id: "fallback-learn-mooc",
      name: "中国大学 MOOC",
      url: "https://www.icourse163.org",
      summary: "中文高校在线开放课程平台。",
      category_name: "学习成长",
      external_only: true,
    },
  ],
  数据分析: [
    {
      id: "fallback-data-kaggle",
      name: "Kaggle",
      url: "https://www.kaggle.com",
      summary: "数据科学竞赛、数据集和 Notebook 平台。",
      category_name: "数据分析",
      external_only: true,
    },
    {
      id: "fallback-data-tableau",
      name: "Tableau",
      url: "https://www.tableau.com",
      summary: "商业智能与数据可视化平台。",
      category_name: "数据分析",
      external_only: true,
    },
    {
      id: "fallback-data-powerbi",
      name: "Power BI",
      url: "https://powerbi.microsoft.com",
      summary: "Microsoft 数据分析与报表平台。",
      category_name: "数据分析",
      external_only: true,
    },
    {
      id: "fallback-data-jupyter",
      name: "Jupyter",
      url: "https://jupyter.org",
      summary: "交互式数据分析与代码笔记本工具。",
      category_name: "数据分析",
      external_only: true,
    },
  ],
  产品运营: [
    {
      id: "fallback-product-feishu",
      name: "飞书",
      url: "https://www.feishu.cn",
      summary: "团队协作、文档和项目沟通平台。",
      category_name: "产品运营",
      external_only: true,
    },
    {
      id: "fallback-product-notion",
      name: "Notion",
      url: "https://www.notion.so",
      summary: "笔记、知识库和项目管理工具。",
      category_name: "产品运营",
      external_only: true,
    },
    {
      id: "fallback-product-processon",
      name: "ProcessOn",
      url: "https://www.processon.com",
      summary: "在线流程图和思维导图工具。",
      category_name: "产品运营",
      external_only: true,
    },
    {
      id: "fallback-product-canva",
      name: "Canva",
      url: "https://www.canva.com",
      summary: "在线设计与内容创作工具。",
      category_name: "产品运营",
      external_only: true,
    },
  ],
};

const careerFallbackSites = {
  学生: ["ChatGPT", "Perplexity", "Notion", "ProcessOn", "Bilibili 学习区"],
  前端开发: [
    "GitHub",
    "MDN Web Docs",
    "Vue 官方文档",
    "Stack Overflow",
    "ChatGPT",
  ],
  后端开发: [
    "GitHub",
    "Flask 官方文档",
    "Stack Overflow",
    "LeetCode",
    "ChatGPT",
  ],
  产品经理: ["Notion", "ProcessOn", "飞书", "Figma", "ChatGPT"],
  "UI/UX 设计师": ["Figma", "Canva", "Iconfont", "Unsplash", "Dribbble"],
  运营: ["ChatGPT", "Canva", "Notion", "飞书", "Trello"],
  教师: ["ChatGPT", "Canva", "ProcessOn", "Bilibili 学习区", "Coursera"],
  自媒体创作者: ["ChatGPT", "Canva", "Unsplash", "Dribbble", "Figma"],
  数据分析师: ["ChatGPT", "Kaggle", "Tableau", "Power BI", "Jupyter"],
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

function categoryFallbackKey(category) {
  const name = String(category?.name || "");
  if (categoryFallbackSites[name]) return name;
  if (name.includes("AI") || name.includes("智能")) return "AI工具";
  if (name.includes("编程") || name.includes("开发")) return "编程开发";
  if (name.includes("设计") || name.includes("素材")) return "设计资源";
  if (name.includes("办公") || name.includes("效率")) return "效率办公";
  if (name.includes("学习") || name.includes("成长") || name.includes("教育")) {
    return "学习成长";
  }
  if (name.includes("数据") || name.includes("分析")) return "数据分析";
  if (name.includes("产品") || name.includes("运营")) return "产品运营";
  return "";
}

function categoryFallback(category) {
  return getCategoryFallbackSites(category);
}

function fillCategorySites(category, sites, limit = 4) {
  return dedupeSites(
    [...normalizeList(sites), ...categoryFallback(category)],
    new Set(),
  ).slice(0, limit);
}

async function loadCategorySites(hotCategories, excludeIds = []) {
  const nextMap = {};
  loadingCategorySites.value = true;
  try {
    await Promise.all(
      hotCategories.map(async (category) => {
        let sites = [];
        try {
          const response = await siteAPI.getSites({
            category_id: category.id,
            limit: 4,
            page_size: 4,
            sort: "hot",
            exclude_ids: idsParam(excludeIds),
          });
          sites = unwrapList(response);
        } catch {
          sites = [];
        }

        if (sites.length < 3) {
          try {
            const fallbackResponse = await siteAPI.getRandom({
              limit: 4,
              category: category.name,
              scene: "category-preview",
              exclude_ids: idsParam([...excludeIds, ...siteIds(sites)]),
            });
            sites = dedupeSites([...sites, ...unwrapList(fallbackResponse)]);
          } catch {
            // Category previews should stay populated from local fallback data.
          }
        }

        nextMap[category.id] = fillCategorySites(category, sites, 4);
      }),
    );
    categorySitesMap.value = nextMap;
  } finally {
    loadingCategorySites.value = false;
  }
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
  const nextValue = (value || keyword.value || "").trim();
  if (!nextValue) return;
  router.push({ path: "/search", query: { q: nextValue } });
}

function goToAiAssistantLogin() {
  router.push({ path: "/login", query: { redirect: "/" } });
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
      .slice(0, 6);

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

    await loadCategorySites(
      categories.value,
      siteIds([
        ...marqueeSites.value,
        ...hotSites.value,
        ...favoriteStackSites.value,
      ]),
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
          } else {
            entry.target.classList.remove("is-visible");
          }
        });
      },
      {
        threshold: 0.16,
        rootMargin: "0px 0px -40px 0px",
      },
    );
  }

  elements.forEach((element, index) => {
    if (element.dataset.revealBound === "1") return;
    element.style.setProperty(
      "--reveal-delay",
      `${Math.min(index * 35, 220)}ms`,
    );
    element.dataset.revealBound = "1";
    revealObserver.observe(element);
  });
}

onMounted(async () => {
  await loadHome();
  await nextTick();
  observeRevealElements();
});

onUpdated(async () => {
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
  grid-template-columns: minmax(0, 1fr);
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

.ai-login-prompt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: min(var(--container), calc(100% - 40px));
  gap: 24px;
  margin: 28px auto 0;
  border: 1px solid rgba(255, 112, 88, 0.18);
  border-radius: 16px;
  background: var(--color-soft-orange);
  padding: 20px 24px;
}

.ai-login-prompt__content {
  min-width: 0;
}

.ai-login-prompt__title {
  margin: 0 0 6px;
  color: var(--color-heading);
  font-size: 16px;
  font-weight: 850;
}

.ai-login-prompt__description {
  margin: 0;
  color: var(--color-text);
  line-height: 1.6;
}

.ai-login-prompt__button {
  flex: 0 0 auto;
  min-height: 42px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #fff;
  padding: 0 16px;
  font: inherit;
  font-weight: 850;
  cursor: pointer;
  transition: var(--transition);
}

.ai-login-prompt__button:hover {
  border-color: var(--color-primary-dark);
  background: var(--color-primary-dark);
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
  .site-grid,
  .ai-login-prompt {
    width: min(100% - 28px, var(--container));
  }

  .site-grid {
    grid-template-columns: 1fr;
  }

  .ai-login-prompt {
    align-items: stretch;
    flex-direction: column;
    gap: 16px;
    padding: 18px;
  }

  .ai-login-prompt__button {
    width: 100%;
  }
}
</style>
