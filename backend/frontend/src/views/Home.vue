<template>
  <div class="page">
    <AppHeader />

    <main id="home" ref="homeMainRef" class="home-main">
      <section
        class="home-screen hero-screen home-first-screen"
        aria-label="首页搜索"
      >
        <div class="hero-content">
          <HeroSearch id="site-search" v-model="keyword" @search="goSearch" />
        </div>
        <p
          class="home-scroll-hint"
          :class="{ 'home-scroll-hint--hidden': !isScrollHintVisible }"
          :aria-hidden="!isScrollHintVisible"
        >
          <span aria-hidden="true">↓</span>
          向下滚动，发现为你的职业量身推荐的工具
        </p>
      </section>

      <div class="home-content">
        <section
          v-reveal-section
          id="career"
          class="home-screen career-screen home-anchor-section career-recommendation-section"
          data-testid="career-recommendations"
        >
          <GuestCareerRecommendation
            v-if="!loggedIn"
            @visit="visitGuestCareerSite"
            @login="goToAiAssistantLogin"
          />
          <template v-else>
            <div ref="careerLayoutRef" class="career-recommendation-layout">
              <section
                ref="careerLeftColumnRef"
                class="career-profile-panel"
                aria-labelledby="career-profile-title"
              >
                <header class="career-profile-panel__header">
                  <span class="eyebrow reveal-child" style="--reveal-delay: 0ms"
                    >问卷画像</span
                  >
                  <h2
                    id="career-profile-title"
                    class="reveal-child reveal-title"
                    style="--reveal-delay: 80ms"
                  >
                    {{
                      questionnaireCompleted
                        ? "你的职业推荐"
                        : loggedIn
                          ? "完成问卷，获取专属推荐"
                          : "登录后获取专属推荐"
                    }}
                  </h2>
                  <p
                    class="reveal-child reveal-description"
                    style="--reveal-delay: 150ms"
                  >
                    推荐会综合你的职业、能力、兴趣、使用目的和资源偏好，并随问卷更新。
                  </p>
                </header>

                <template
                  v-if="
                    loggedIn &&
                    questionnaireStatus === 'ready' &&
                    questionnaireCompleted
                  "
                >
                  <div
                    v-if="careerAbilityTags.length"
                    class="career-tag-groups reveal-child"
                    style="--reveal-delay: 200ms"
                  >
                    <div class="career-tag-group">
                      <span>能力标签</span>
                      <div>
                        <b
                          v-for="tag in careerAbilityTags"
                          :key="`ability-${tag}`"
                          >{{ tag }}</b
                        >
                      </div>
                    </div>
                  </div>

                  <div
                    class="career-selection reveal-child"
                    style="--reveal-delay: 230ms"
                  >
                    <h3 id="career-selection-title">选择职业</h3>
                    <div
                      class="career-options"
                      aria-labelledby="career-selection-title"
                    >
                      <button
                        v-for="career in careerRecommendations"
                        :key="career.code"
                        type="button"
                        class="career-option"
                        :class="{
                          'career-option--active':
                            activeCareerCode === career.code,
                        }"
                        :aria-pressed="activeCareerCode === career.code"
                        @click="selectCareer(career)"
                      >
                        <span class="career-option__main">
                          <strong>{{ career.label }}</strong>
                        </span>
                        <b class="career-option__score"
                          >{{ career.match_score }}%</b
                        >
                      </button>
                    </div>
                  </div>

                  <RouterLink
                    class="career-profile-panel__link reveal-child"
                    style="--reveal-delay: 650ms"
                    to="/questionnaire"
                  >
                    更新问卷
                  </RouterLink>
                </template>

                <template
                  v-else-if="loggedIn && questionnaireStatus === 'empty'"
                >
                  <p
                    class="career-profile-panel__empty reveal-child reveal-description"
                    style="--reveal-delay: 180ms"
                  >
                    提交问卷后，这里会显示动态职业方向和匹配原因。
                  </p>
                  <RouterLink
                    class="career-profile-panel__action reveal-child"
                    style="--reveal-delay: 230ms"
                    to="/questionnaire"
                  >
                    去完成问卷
                  </RouterLink>
                </template>

                <template
                  v-else-if="loggedIn && questionnaireStatus === 'error'"
                >
                  <p
                    class="career-profile-panel__empty reveal-child reveal-description"
                    style="--reveal-delay: 180ms"
                  >
                    暂时无法确认问卷状态，请稍后重试。
                  </p>
                  <button
                    type="button"
                    class="career-profile-panel__action reveal-child"
                    style="--reveal-delay: 230ms"
                    @click="retryCareerSites"
                  >
                    重新加载
                  </button>
                </template>

                <p
                  v-else-if="loggedIn"
                  class="career-profile-panel__empty career-profile-panel__empty--loading reveal-child reveal-description"
                  style="--reveal-delay: 180ms"
                >
                  正在检查问卷状态…
                </p>

                <button
                  v-else
                  type="button"
                  class="career-profile-panel__action reveal-child"
                  style="--reveal-delay: 230ms"
                  @click="goToAiAssistantLogin"
                >
                  登录后开始问卷
                </button>
              </section>

              <div class="career-results" aria-live="polite">
                <header class="career-results__heading">
                  <span
                    class="eyebrow reveal-child"
                    style="--reveal-delay: 40ms"
                    >职业推荐</span
                  >
                  <div class="career-results__title-row">
                    <div>
                      <AnimatedPageTitle
                        v-if="activeCareerCode"
                        class="reveal-child reveal-title"
                        style="--reveal-delay: 100ms"
                        as="h2"
                        :animation="false"
                      >
                        适合「{{ selectedOccupationLabel }}」的网站工具
                      </AnimatedPageTitle>
                      <AnimatedPageTitle
                        v-else
                        class="reveal-child reveal-title"
                        style="--reveal-delay: 100ms"
                        as="h2"
                        :animation="false"
                      >
                        完成问卷后发现更合适的网站工具
                      </AnimatedPageTitle>
                    </div>
                    <button
                      v-if="activeCareerCode"
                      type="button"
                      class="career-refresh-button reveal-child"
                      style="--reveal-delay: 680ms"
                      data-testid="career-refresh-batch"
                      :disabled="!canRefreshCareerBatch"
                      aria-label="换一批职业网站"
                      @click.stop.prevent="refreshCareerBatch"
                    >
                      <RefreshCw :size="16" aria-hidden="true" />
                      <span>换一批</span>
                    </button>
                  </div>
                  <p
                    class="reveal-child reveal-description"
                    style="--reveal-delay: 170ms"
                  >
                    {{
                      activeCareerCode
                        ? "网站会按照当前问卷画像和所选职业实时排序。"
                        : "提交问卷后，这里会展示与职业推荐对应的网站和工具。"
                    }}
                  </p>
                </header>

                <div
                  v-if="careerStatus === 'idle'"
                  class="career-request-state career-request-state--idle reveal-child reveal-description"
                  style="--reveal-delay: 240ms"
                >
                  <span aria-hidden="true">↗</span>
                  <strong>{{
                    loggedIn ? "等待问卷推荐" : "登录后查看职业推荐"
                  }}</strong>
                  <p>
                    {{
                      loggedIn
                        ? "提交问卷后，系统会生成你的职业和网站推荐。"
                        : "登录并提交问卷后，系统会生成你的职业和网站推荐。"
                    }}
                  </p>
                </div>

                <div
                  v-else-if="careerStatus === 'loading'"
                  class="career-skeleton-grid"
                  aria-label="正在加载职业推荐"
                >
                  <article
                    v-for="index in visibleCareerSiteCount"
                    :key="index"
                    class="career-skeleton-card reveal-child reveal-card"
                    :style="revealCardStyle(index - 1, 240)"
                  >
                    <span></span>
                    <b></b>
                    <i></i>
                  </article>
                </div>

                <div
                  v-else-if="careerStatus === 'error'"
                  class="career-request-state career-request-state--error reveal-child reveal-description"
                  style="--reveal-delay: 240ms"
                  role="alert"
                >
                  <strong>职业推荐加载失败</strong>
                  <p>{{ sitesError }}</p>
                  <button type="button" @click="retryCareerSites">
                    重新加载
                  </button>
                </div>

                <EmptyState
                  v-else-if="careerStatus === 'empty'"
                  class="reveal-child reveal-description"
                  style="--reveal-delay: 240ms"
                  title="暂无匹配的网站工具"
                  description="问卷已完成，但当前资源库还没有与推荐职业关联的网站。"
                />

                <div v-else-if="careerStatus === 'success'">
                  <div
                    ref="careerRightGridRef"
                    class="career-site-grid"
                    data-testid="career-site-batch"
                  >
                    <SiteCard
                      v-for="site in visibleCareerSites"
                      :key="`${activeCareerCode}-${activeCareerBatchIndex}-${site.id || normalizeUrl(site.url) || site.name}`"
                      class="reveal-child reveal-card"
                      :class="{ 'card-refresh-item': careerBatchHasChanged }"
                      :style="
                        revealCardStyle(visibleCareerSites.indexOf(site), 240)
                      "
                      :site="site"
                      variant="career"
                      :show-reason="true"
                      @visit="visitSite"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div
              v-if="careerStatus === 'success'"
              class="ai-login-prompt career-section-cta reveal-child"
              style="--reveal-delay: 720ms"
              :class="{ 'ai-login-prompt--authenticated': loggedIn }"
            >
              <div class="ai-login-prompt__content">
                <p class="ai-login-prompt__title">
                  {{
                    loggedIn ? "还没有找到合适的网站？" : "没有找到合适的网站？"
                  }}
                </p>
                <p class="ai-login-prompt__description">
                  {{
                    loggedIn
                      ? "告诉知航AI你想完成什么，让它从平台已收录的网站中帮你筛选。"
                      : "登录后描述你的具体需求，知航AI将为你推荐更适合的网站。"
                  }}
                </p>
              </div>
              <button
                type="button"
                class="ai-login-prompt__button"
                @click="handleAiAssistantEntry"
              >
                {{ loggedIn ? "询问知航AI助手" : "登录并使用知航AI助手" }}
              </button>
            </div>
          </template>
        </section>

        <section
          v-reveal-section
          id="recommend-tools"
          class="home-screen popular-screen home-anchor-section"
          data-testid="featured-recommendations"
        >
          <RecommendSection :sites="featuredRecommendationSites" />
          <ToolMarquee
            v-if="!isCategoryScreenActive"
            data-testid="popular-sites-marquee"
            :sites="marqueeSites"
            @visit="visitSite"
          />
        </section>

        <section
          v-reveal-section
          id="tools"
          ref="categoryScreenRef"
          class="home-screen category-screen home-anchor-section"
          data-testid="popular-categories"
        >
          <CategorySection
            :categories="categories"
            :category-sites-map="categorySitesMap"
            :loading-category-sites="loadingCategorySites"
            :refreshing="categoryRefreshing"
            :status="categoryStatus"
            :error="categoryError"
            @retry="retryCategories"
            @visit-site="visitSite"
          />
        </section>

        <section
          v-if="commonToolsCandidatePool.length"
          v-reveal-section
          id="favorite-stack"
          ref="commonToolsSectionRef"
          class="home-screen favorite-screen home-anchor-section"
          data-testid="common-tools-recommendations"
        >
          <FavoriteStack :sites="currentCommonTools" @visit="visitSite" />
        </section>
      </div>
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
  watch,
} from "vue";
import { RefreshCw } from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";
import AnimatedPageTitle from "../components/common/AnimatedPageTitle.vue";
import EmptyState from "../components/common/EmptyState.vue";
import AiSiteAssistant from "../components/ai/AiSiteAssistant.vue";
import CategorySection from "../components/home/CategorySection.vue";
import FavoriteStack from "../components/home/FavoriteStack.vue";
import GuestCareerRecommendation from "../components/home/GuestCareerRecommendation.vue";
import HeroSearch from "../components/home/HeroSearch.vue";
import RecommendSection from "../components/home/RecommendSection.vue";
import ToolMarquee from "../components/home/ToolMarquee.vue";
import AppFooter from "../components/layout/AppFooter.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import SiteCard from "../components/site/SiteCard.vue";
import { featuredWebsites } from "../data/featuredWebsites";
import {
  websiteCatalog,
  websiteCatalogCategories,
} from "../data/websiteCatalog";
import { useAiAssistantStore } from "../stores/aiAssistant";
import { useFavoritesStore } from "../stores/favorites";
import { useUserStore } from "../stores/user";
import {
  categoryAPI,
  careerAPI,
  normalizeSiteKey,
  normalizeCareerSite,
  normalizeCareerSiteList,
  normalizeWebsite,
  normalizeWebsiteList,
  normalizeUrl,
  siteAPI,
  unwrapCareerRecommendationResponse,
  unwrapList,
  unwrapResponse,
} from "../utils/api";
import { getAccessToken, isValidAuthToken } from "../utils/auth";
import { runListRequest } from "../utils/listRequestState.js";
import {
  createCommonToolsQueue,
  dedupeCommonTools,
  isEligibleCommonTool,
  takeNextCommonToolsBatch,
} from "../utils/commonToolsRotation.js";
import { visitSite as openVisitedSite } from "../utils/siteVisit";
import { trackImpressions } from "../utils/behaviorTracker";
import { errorToast, successToast } from "../utils/toast";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const aiAssistantStore = useAiAssistantStore();
const favoriteStore = useFavoritesStore();
// 分类接口需要聚合数据库数据；在本地环境的首次查询可能超过默认的 6 秒。
// 与 API 客户端的默认请求超时保持一致，避免把可用的慢响应误判为加载失败。
const HOME_RESOURCE_TIMEOUT_MS = 15_000;
const WEBSITE_CACHE_KEY = "zhihui:website-catalog:v3";
const WEBSITE_CACHE_VERSION = 3;
const WEBSITE_CACHE_TTL_MS = 10 * 60 * 1000;
const WEBSITE_PAGE_SIZE = 100;
const CAREER_BATCH_SIZE = 16;
const CAREER_SITE_POOL_MAX = 48;
const CAREER_CACHE_NAMESPACE = "zhihui:career-recommendation";
const CAREER_ALGORITHM_VERSION = "career-v4";
const HOME_DESKTOP_SCROLL_QUERY = "(min-width: 1024px)";
const HOME_WHEEL_THRESHOLD = 10;
const HOME_SCROLL_DURATION_MS = 600;
const COMMON_TOOLS_BATCH_SIZE = 4;
const COMMON_TOOLS_ENTER_RATIO = 0.65;
const HOME_NATIVE_WHEEL_SELECTOR = [
  '[role="dialog"]',
  ".modal",
  ".dropdown",
  ".engine-menu",
  ".search-suggestions",
  ".ai-site-assistant",
].join(", ");
const builtinWebsites = normalizeWebsiteList(websiteCatalog);
const builtinCategories = websiteCatalogCategories;
const keyword = ref("");
const categories = ref(builtinCategories);
const categorySitesMap = ref(
  createCategorySitesMap(builtinWebsites, builtinCategories),
);
const loadingCategorySites = ref(false);
const categoryRefreshing = ref(builtinWebsites.length > 0);
const categoryStatus = ref(builtinWebsites.length > 0 ? "success" : "loading");
const categoryError = ref("");
const recommended = ref([]);
const hotSites = ref([]);
const marqueeSites = ref([]);
const favoriteStackSites = ref([]);
const shuffledCommonTools = ref([]);
const commonToolsCursor = ref(0);
const currentCommonTools = ref([]);
const commonToolsSectionVisible = ref(false);
const latestSites = ref([]);
const isScrollHintVisible = ref(true);
const loading = ref(false);
const error = ref("");
const hotError = ref("");
const activeCareerCode = ref("");
const recommendations = ref([]);
const sitesByCareer = ref({});
const sitesLoading = ref(false);
const sitesError = ref("");
const careerBatchIndex = ref(0);
const careerBatchHasChanged = ref(false);
const batchIndexByCareer = ref({});
const questionnaireVersion = ref("");
const careerAbilityTags = ref([]);
const careerInterestTags = ref([]);
const questionnaireCompleted = ref(false);
const questionnaireStatus = ref("idle");
const careerStatus = ref("idle");
const careerRecommendations = recommendations;
const homeMainRef = ref(null);
const categoryScreenRef = ref(null);
const currentSectionIndex = ref(0);
const careerLayoutRef = ref(null);
const careerLeftColumnRef = ref(null);
const careerRightGridRef = ref(null);
const commonToolsSectionRef = ref(null);
const visibleCareerSiteCount = ref(CAREER_BATCH_SIZE);

const commonToolsCandidatePool = computed(() =>
  buildCommonToolsCandidatePool(),
);

const featuredRecommendationSites = computed(() => {
  const candidates = [
    ...flattenCategorySites(categorySitesMap.value),
    ...recommended.value,
    ...hotSites.value,
    ...latestSites.value,
  ];
  const candidateByKey = new Map(
    candidates
      .map((site) => [normalizeSiteKey(site), site])
      .filter(([key]) => key),
  );

  return featuredWebsites.map((featuredSite) => {
    const matchedSite = candidateByKey.get(normalizeSiteKey(featuredSite));
    const hasDatabaseId = /^\d+$/.test(String(matchedSite?.id || ""));
    if (!hasDatabaseId) return featuredSite;
    return {
      ...featuredSite,
      ...matchedSite,
      icon: matchedSite.logo_url || matchedSite.logo || featuredSite.icon,
      category: matchedSite.category_name || featuredSite.category,
    };
  });
});

const isCategoryScreenActive = computed(() => {
  const categoryScreen = categoryScreenRef.value;
  if (!categoryScreen) return route.hash === "#tools";
  const categoryIndex = getHomeScreens().indexOf(categoryScreen);
  return categoryIndex >= 0 && currentSectionIndex.value === categoryIndex;
});

function getFullCareerBatchCount(sites = []) {
  return Math.ceil(sites.length / CAREER_BATCH_SIZE);
}

const activeCareer = computed(
  () =>
    recommendations.value.find(
      (career) =>
        (career.careerCode || career.career_code || career.code) ===
        activeCareerCode.value,
    ) || null,
);
const activeSites = computed(() => {
  if (!activeCareerCode.value) return [];
  return sitesByCareer.value[activeCareerCode.value] || [];
});
const activeCareerSitesPool = computed(() => {
  const careerCode = activeCareerCode.value;
  if (!careerCode) return [];

  const groupedSites = sitesByCareer.value?.[careerCode];
  const career = activeCareer.value;
  const fallbackSites =
    career?.sites || career?.websites || career?.recommendedSites || [];
  const sites =
    Array.isArray(groupedSites) && groupedSites.length
      ? groupedSites
      : fallbackSites;

  return ensureCareerSitePool(careerCode, Array.isArray(sites) ? sites : []);
});
const careerBatchCount = computed(() =>
  getFullCareerBatchCount(activeCareerSitesPool.value),
);
const canRefreshCareerBatch = computed(
  () => !sitesLoading.value && careerBatchCount.value > 1,
);
const activeCareerBatchIndex = computed(() => {
  const careerCode = activeCareerCode.value;
  if (
    Object.prototype.hasOwnProperty.call(batchIndexByCareer.value, careerCode)
  ) {
    return Number(batchIndexByCareer.value[careerCode]) || 0;
  }
  return Number(careerBatchIndex.value) || 0;
});
const visibleCareerSites = computed(() => {
  const careerCode = activeCareerCode.value;
  const pool = activeCareerSitesPool.value;
  if (!pool.length) return [];

  const batchCount = getFullCareerBatchCount(pool);
  if (!batchCount) return [];
  const requestedIndex = Number(activeCareerBatchIndex.value) || 0;
  const safeIndex = ((requestedIndex % batchCount) + batchCount) % batchCount;
  const start = safeIndex * CAREER_BATCH_SIZE;
  const batchId = `${pool[0]?.recommendation_session_id || pool[0]?.batch_id || "career"}:${careerCode}:${safeIndex}`;
  const orderedPool = [...pool.slice(start), ...pool.slice(0, start)];
  return orderedPool.slice(0, visibleCareerSiteCount.value).map((site) => ({
    ...site,
    visit_source: "career_recommend",
    recommendation_batch_id: batchId,
  }));
});

let careerLayoutResizeObserver = null;
let careerLayoutFrame = 0;
let careerLayoutMeasureToken = 0;
let lastCareerResponsiveLimit = 0;

function getCareerResponsiveSiteLimit() {
  if (typeof window === "undefined") return CAREER_BATCH_SIZE;
  if (window.innerWidth < 768) return 8;
  if (window.innerWidth < 1024) return 16;

  const viewportHeight = window.innerHeight;
  if (window.innerWidth < 1200) {
    if (viewportHeight >= 1180) return 12;
    if (viewportHeight >= 980) return 9;
    return 6;
  }

  if (viewportHeight >= 1180) return 16;
  if (viewportHeight >= 980) return 12;
  return 8;
}

function getCareerGridColumnCount() {
  const grid = careerRightGridRef.value;
  if (!grid || typeof window === "undefined") return 1;
  const columns = window
    .getComputedStyle(grid)
    .gridTemplateColumns.split(" ")
    .filter(Boolean).length;
  return Math.max(1, columns);
}

async function measureAndFillCareerSites() {
  const token = ++careerLayoutMeasureToken;
  const total = activeCareerSitesPool.value.length;
  if (careerStatus.value !== "success" || !total) return;
  await nextTick();
  if (token !== careerLayoutMeasureToken) return;

  const left = careerLeftColumnRef.value;
  const grid = careerRightGridRef.value;
  if (!left || !grid) return;

  const maximum = Math.min(total, getCareerResponsiveSiteLimit());
  const leftTargetHeight = left.getBoundingClientRect().height * 0.85;
  const rightHeight = grid.getBoundingClientRect().height;
  if (
    rightHeight >= leftTargetHeight ||
    visibleCareerSiteCount.value >= maximum
  )
    return;

  const columns = getCareerGridColumnCount();
  const firstCardHeight =
    grid.firstElementChild?.getBoundingClientRect().height || 0;
  const rowGap = Number.parseFloat(window.getComputedStyle(grid).rowGap) || 0;
  const rowHeight = Math.max(1, firstCardHeight + rowGap);
  const missingRows = Math.max(
    1,
    Math.ceil((leftTargetHeight - rightHeight) / rowHeight),
  );
  visibleCareerSiteCount.value = Math.min(
    maximum,
    visibleCareerSiteCount.value + missingRows * columns,
  );
}

function scheduleCareerLayoutMeasurement({ reset = false } = {}) {
  const responsiveLimit = getCareerResponsiveSiteLimit();
  const breakpointChanged = responsiveLimit !== lastCareerResponsiveLimit;
  lastCareerResponsiveLimit = responsiveLimit;
  if (reset || breakpointChanged) {
    visibleCareerSiteCount.value = Math.min(
      CAREER_BATCH_SIZE,
      responsiveLimit,
      activeCareerSitesPool.value.length,
    );
  } else if (visibleCareerSiteCount.value > responsiveLimit) {
    visibleCareerSiteCount.value = responsiveLimit;
  }
  if (typeof window === "undefined") return;
  window.cancelAnimationFrame(careerLayoutFrame);
  careerLayoutFrame = window.requestAnimationFrame(() => {
    void measureAndFillCareerSites();
  });
}

function observeCareerLayout() {
  careerLayoutResizeObserver?.disconnect();
  if (typeof ResizeObserver === "undefined") return;
  careerLayoutResizeObserver = new ResizeObserver(() => {
    scheduleCareerLayoutMeasurement();
  });
  if (careerLayoutRef.value)
    careerLayoutResizeObserver.observe(careerLayoutRef.value);
  if (careerLeftColumnRef.value)
    careerLayoutResizeObserver.observe(careerLeftColumnRef.value);
  if (careerRightGridRef.value)
    careerLayoutResizeObserver.observe(careerRightGridRef.value);
}

watch(
  [
    activeCareerCode,
    activeCareerBatchIndex,
    activeCareerSitesPool,
    careerStatus,
  ],
  async () => {
    await nextTick();
    observeCareerLayout();
    scheduleCareerLayoutMeasurement({ reset: true });
  },
  { flush: "post" },
);

let lastImpressionBatchKey = "";
watch(
  [visibleCareerSites, activeCareerCode, activeCareerBatchIndex],
  async ([sites, careerCode, batchIndex]) => {
    if (
      !loggedIn.value ||
      !careerCode ||
      !Array.isArray(sites) ||
      !sites.length
    )
      return;
    const first = sites[0] || {};
    const session =
      first.recommendation_session_id || first.batch_id || "career";
    const batchId = `${session}:${careerCode}:${Number(batchIndex) || 0}`;
    if (batchId === lastImpressionBatchKey) return;
    lastImpressionBatchKey = batchId;
    await nextTick();
    void trackImpressions(sites, {
      source: "personalized_recommendation",
      recommendation_batch_id: batchId,
      questionnaire_version: first.questionnaire_version,
      profile_version: first.profile_version,
      profile_schema_version:
        first.profile_schema_version || first.profile_version,
      metadata: {
        display_batch_index: Number(batchIndex) || 0,
        candidate_pool_id: first.candidate_pool_id,
        surface: "home_career",
      },
    });
  },
  { deep: false },
);
let previousWatchedCareerCode = "";
watch(
  activeCareerCode,
  (newCode) => {
    if (!newCode) return;

    const careerChanged =
      Boolean(previousWatchedCareerCode) &&
      previousWatchedCareerCode !== newCode;
    const requestedIndex = careerChanged
      ? 0
      : Number(batchIndexByCareer.value[newCode]) || 0;
    const safeIndex = careerBatchCount.value
      ? ((requestedIndex % careerBatchCount.value) + careerBatchCount.value) %
        careerBatchCount.value
      : 0;
    careerBatchIndex.value = safeIndex;
    if (batchIndexByCareer.value[newCode] !== safeIndex) {
      batchIndexByCareer.value = {
        ...batchIndexByCareer.value,
        [newCode]: safeIndex,
      };
    }
    previousWatchedCareerCode = newCode;
  },
  { immediate: true },
);
const careerSites = computed(() => activeSites.value);
const selectedOccupationLabel = computed(
  () => activeCareer.value?.careerName || activeCareer.value?.label || "",
);
const loggedIn = computed(
  () => userStore.isLoggedIn && isValidAuthToken(getAccessToken()),
);
const careerAuthIdentity = computed(() => {
  if (!loggedIn.value) return "";
  return getCareerCacheUserId() || "authenticated";
});
let homeScreenObserver = null;
let commonToolsObserver = null;
let observedCommonToolsSection = null;
let homeScrollLocked = false;
let homeScrollAnimationFrame = 0;
let homeSnapRestoreFrame = 0;
let homeSnapRestoreSecondFrame = 0;
let homeSectionSyncFrame = 0;
const observedHomeScreens = new Set();
const homeScreenIntersectionRatios = new Map();
let homeRequestController = null;
let categoryRequestController = null;
let categoryRequestId = 0;

function getCareerCacheUserId() {
  const info = userStore.userInfo || {};
  return String(info.id || info.user_id || info.username || "").trim();
}

function getCareerCacheStorage() {
  try {
    return typeof sessionStorage === "undefined" ? null : sessionStorage;
  } catch {
    return null;
  }
}

function getCareerCacheIndexKey(userId) {
  return `${CAREER_CACHE_NAMESPACE}:${encodeURIComponent(userId)}:latest`;
}

function getCareerCacheKey(userId, version) {
  return `${CAREER_CACHE_NAMESPACE}:${encodeURIComponent(userId)}:${encodeURIComponent(version)}:${CAREER_ALGORITHM_VERSION}`;
}

function clearCareerCache(userId = getCareerCacheUserId()) {
  const storage = getCareerCacheStorage();
  if (!storage || !userId) return;

  const indexKey = getCareerCacheIndexKey(userId);
  try {
    const pointer = JSON.parse(storage.getItem(indexKey) || "null");
    if (pointer?.cacheKey) storage.removeItem(pointer.cacheKey);
    storage.removeItem(indexKey);
  } catch {
    // A disabled or corrupted cache must not block logout or revalidation.
  }
}

function readCareerCache(userId) {
  const storage = getCareerCacheStorage();
  if (!storage || !userId) return null;

  try {
    const pointer = JSON.parse(
      storage.getItem(getCareerCacheIndexKey(userId)) || "null",
    );
    if (
      !pointer ||
      pointer.userId !== userId ||
      pointer.algorithmVersion !== CAREER_ALGORITHM_VERSION ||
      !pointer.questionnaireVersion
    ) {
      return null;
    }

    const cache = JSON.parse(storage.getItem(pointer.cacheKey) || "null");
    if (
      !cache ||
      cache.userId !== userId ||
      cache.questionnaireVersion !== pointer.questionnaireVersion ||
      cache.algorithmVersion !== CAREER_ALGORITHM_VERSION ||
      !Array.isArray(cache.recommendations)
    ) {
      return null;
    }
    return cache;
  } catch {
    return null;
  }
}

function persistCareerCache() {
  const storage = getCareerCacheStorage();
  const userId = getCareerCacheUserId();
  if (!storage || !userId || !questionnaireVersion.value) return;

  const version = String(questionnaireVersion.value);
  const cacheKey = getCareerCacheKey(userId, version);
  const cache = {
    userId,
    questionnaireVersion: version,
    algorithmVersion: CAREER_ALGORITHM_VERSION,
    questionnaireCompleted: questionnaireCompleted.value,
    recommendations: recommendations.value,
    sitesByCareer: sitesByCareer.value,
    abilityTags: careerAbilityTags.value,
    interestTags: careerInterestTags.value,
    activeCareerCode: activeCareerCode.value,
    batchIndexByCareer: batchIndexByCareer.value,
    generatedAt: new Date().toISOString(),
  };

  try {
    storage.setItem(cacheKey, JSON.stringify(cache));
    storage.setItem(
      getCareerCacheIndexKey(userId),
      JSON.stringify({
        userId,
        questionnaireVersion: version,
        algorithmVersion: CAREER_ALGORITHM_VERSION,
        cacheKey,
      }),
    );
  } catch {
    // A full or disabled session storage must not block recommendations.
  }
}

function restoreCareerCache() {
  const cache = readCareerCache(getCareerCacheUserId());
  if (!cache) return false;

  const normalized = normalizeRecommendations({
    recommendations: cache.recommendations,
  });
  if (!normalized.list.length) return false;

  const cachedSitesByCareer =
    cache.sitesByCareer && typeof cache.sitesByCareer === "object"
      ? cache.sitesByCareer
      : {};
  const restoredSitesByCareer = {};
  const restoredRecommendations = normalized.list.map((career) => {
    const cachedSites = Array.isArray(cachedSitesByCareer[career.careerCode])
      ? normalizeCareerSiteList(cachedSitesByCareer[career.careerCode])
      : [];
    const sites = ensureCareerSitePool(
      career.careerCode,
      cachedSites.length ? cachedSites : career.sites || [],
    );
    restoredSitesByCareer[career.careerCode] = sites;
    return {
      ...career,
      sites,
      websites: sites,
    };
  });

  recommendations.value = restoredRecommendations;
  sitesByCareer.value = restoredSitesByCareer;
  careerAbilityTags.value = Array.isArray(cache.abilityTags)
    ? cache.abilityTags
    : [];
  careerInterestTags.value = Array.isArray(cache.interestTags)
    ? cache.interestTags
    : [];
  questionnaireCompleted.value = Boolean(cache.questionnaireCompleted);
  questionnaireVersion.value = String(cache.questionnaireVersion);
  batchIndexByCareer.value =
    cache.batchIndexByCareer && typeof cache.batchIndexByCareer === "object"
      ? cache.batchIndexByCareer
      : {};

  const cachedCareer = normalized.list.some(
    (career) => career.careerCode === cache.activeCareerCode,
  );
  activeCareerCode.value = cachedCareer
    ? cache.activeCareerCode
    : normalized.list[0].careerCode;
  careerBatchIndex.value =
    Number(batchIndexByCareer.value[activeCareerCode.value]) || 0;
  sitesLoading.value = false;
  questionnaireStatus.value = questionnaireCompleted.value ? "ready" : "empty";
  careerStatus.value = activeSites.value.length ? "success" : "empty";
  return true;
}

function clearCareerState() {
  latestCareerRequestId += 1;
  latestCareerSelectionId += 1;
  activeCareerCode.value = "";
  careerBatchIndex.value = 0;
  batchIndexByCareer.value = {};
  recommendations.value = [];
  sitesByCareer.value = {};
  sitesLoading.value = false;
  sitesError.value = "";
  questionnaireVersion.value = "";
  careerAbilityTags.value = [];
  careerInterestTags.value = [];
  questionnaireCompleted.value = false;
  questionnaireStatus.value = "idle";
  careerStatus.value = "idle";
  lastImpressionBatchKey = "";
}

let careerInitializationPromise = null;
let careerInitializationIdentity = "";

function initializeCareerRecommendations() {
  const identity = careerAuthIdentity.value;
  if (!identity) return Promise.resolve();
  if (
    careerInitializationPromise &&
    careerInitializationIdentity === identity
  ) {
    return careerInitializationPromise;
  }

  careerInitializationIdentity = identity;
  const restored = restoreCareerCache();
  careerInitializationPromise = loadCareerRecommendations({
    keepExistingData: restored,
  }).finally(() => {
    if (careerInitializationIdentity === identity) {
      careerInitializationPromise = null;
    }
  });
  return careerInitializationPromise;
}

watch(careerAuthIdentity, async (identity, previousIdentity) => {
  if (!identity) {
    if (previousIdentity && previousIdentity !== "authenticated") {
      clearCareerCache(previousIdentity);
    }
    clearFavoriteState();
    aiAssistantStore.closeAssistant();
    clearCareerState();
    return;
  }

  if (identity !== previousIdentity) clearCareerState();
  await loadFavoriteState();
  await initializeCareerRecommendations();
});

// A questionnaire submitted from the top-level modal invalidates the career
// cache and immediately refreshes this page without a hard reload.
watch(
  () => userStore.questionnaireRevision,
  async (revision, previousRevision) => {
    if (!revision || revision === previousRevision || !loggedIn.value) return;
    clearCareerCache();
    await loadCareerRecommendations({ keepExistingData: false });
  },
);

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

function getSettledData(result, fallback = []) {
  if (result.status !== "fulfilled") return normalizeWebsiteList(fallback);
  return normalizeWebsiteList(result.value);
}

function normalizeList(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function getWebsiteCategoryName(website = {}, categoryList = []) {
  const relatedCategory = website.category;
  const relatedName =
    relatedCategory && typeof relatedCategory === "object"
      ? relatedCategory.name
      : relatedCategory;
  const categoryId =
    website.category_id ?? website.categoryId ?? relatedCategory?.id;
  return String(
    website.category_name ||
      website.categoryName ||
      relatedName ||
      categoryList.find(
        (category) => String(category.id) === String(categoryId),
      )?.name ||
      "",
  ).trim();
}

function mergeWebsiteLists(...lists) {
  const merged = new Map();
  lists.flatMap(normalizeList).forEach((site) => {
    const normalized = normalizeWebsite(site);
    const key = normalizeSiteKey(normalized);
    if (!key) return;
    merged.set(key, { ...(merged.get(key) || {}), ...normalized });
  });
  return [...merged.values()];
}

function buildCommonToolsCandidatePool() {
  const runtimeSites = mergeWebsiteLists(
    flattenCategorySites(categorySitesMap.value),
    latestSites.value,
    recommended.value,
    hotSites.value,
    favoriteStackSites.value,
  );
  const runtimeByKey = new Map(
    runtimeSites
      .map((site) => [normalizeSiteKey(site), site])
      .filter(([key]) => key),
  );

  const catalogSites = builtinWebsites.map((catalogSite) => {
    const key = normalizeSiteKey(catalogSite);
    const runtimeSite = runtimeByKey.get(key);
    if (!runtimeSite) return catalogSite;
    const description =
      runtimeSite.shortDescription ||
      runtimeSite.summary ||
      catalogSite.shortDescription ||
      catalogSite.summary ||
      "";
    return normalizeWebsite({
      ...catalogSite,
      ...runtimeSite,
      summary: description,
      shortDescription: description,
      category_id: catalogSite.category_id,
      category_name: catalogSite.category_name,
      logo_url: runtimeSite.logo_url || catalogSite.logo_url,
    });
  });

  return dedupeCommonTools(catalogSites).filter(isEligibleCommonTool);
}

function resetCommonToolsQueue(candidates) {
  shuffledCommonTools.value = createCommonToolsQueue(
    candidates,
    currentCommonTools.value,
  );
  commonToolsCursor.value = 0;
  if (!candidates.length) currentCommonTools.value = [];
}

function showNextCommonToolsBatch() {
  const next = takeNextCommonToolsBatch({
    candidates: commonToolsCandidatePool.value,
    shuffled: shuffledCommonTools.value,
    cursor: commonToolsCursor.value,
    previousBatch: currentCommonTools.value,
    batchSize: COMMON_TOOLS_BATCH_SIZE,
  });
  shuffledCommonTools.value = next.shuffled;
  commonToolsCursor.value = next.cursor;
  currentCommonTools.value = next.batch;
}

watch(
  commonToolsCandidatePool,
  (candidates) => resetCommonToolsQueue(candidates),
  { immediate: true },
);

function mergeCategoryLists(...lists) {
  const merged = new Map();
  lists.flatMap(normalizeList).forEach((category) => {
    const name = String(category?.name || category || "").trim();
    if (!name) return;
    const key = name.toLocaleLowerCase();
    merged.set(key, {
      ...(merged.get(key) || {}),
      ...(typeof category === "object" ? category : { name }),
      name,
    });
  });
  return [...merged.values()];
}

function deriveCategoriesFromWebsites(websites) {
  const seen = new Map();
  normalizeList(websites).forEach((website) => {
    const name = getWebsiteCategoryName(website);
    if (!name || seen.has(name)) return;
    seen.set(name, {
      id: `derived-${name}`,
      name,
      description: "浏览该分类下收录的网站资源。",
    });
  });
  return [...seen.values()];
}

function createCategorySitesMap(websites, categoryList = []) {
  const map = {};
  const categoryByName = new Map(
    normalizeList(categoryList).map((category) => [
      String(category.name || "").trim(),
      category,
    ]),
  );

  normalizeList(categoryList).forEach((category) => {
    map[category.id] = [];
  });

  mergeWebsiteLists(websites).forEach((website) => {
    const categoryName = getWebsiteCategoryName(website, categoryList);
    const category = categoryByName.get(categoryName);
    const key = category?.id ?? website.category_id ?? categoryName;
    if (!key) return;
    if (!map[key]) map[key] = [];
    map[key] = mergeWebsiteLists(map[key], [
      { ...website, category_name: categoryName || website.category_name },
    ]);
  });
  return map;
}

function flattenCategorySites(siteMap) {
  return Object.values(siteMap || {}).flatMap((sites) => normalizeList(sites));
}

function readWebsiteCache() {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(WEBSITE_CACHE_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (
      !parsed ||
      parsed.version !== WEBSITE_CACHE_VERSION ||
      !Array.isArray(parsed.websites) ||
      Date.now() - Number(parsed.timestamp || 0) > WEBSITE_CACHE_TTL_MS
    ) {
      return [];
    }
    return normalizeWebsiteList(parsed.websites);
  } catch {
    return [];
  }
}

function writeWebsiteCache(websites) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      WEBSITE_CACHE_KEY,
      JSON.stringify({
        version: WEBSITE_CACHE_VERSION,
        timestamp: Date.now(),
        websites: mergeWebsiteLists(websites),
      }),
    );
  } catch {
    // 缓存不可用时不影响网站列表渲染。
  }
}

function restoreImmediateData() {
  const cachedWebsites = readWebsiteCache();
  const immediateWebsites = mergeWebsiteLists(cachedWebsites, builtinWebsites);
  const immediateCategories = mergeCategoryLists(
    builtinCategories,
    deriveCategoriesFromWebsites(immediateWebsites),
  );
  categories.value = immediateCategories;
  categorySitesMap.value = createCategorySitesMap(
    immediateWebsites,
    immediateCategories,
  );
  categoryStatus.value = immediateWebsites.length > 0 ? "success" : "loading";
  categoryRefreshing.value = immediateWebsites.length > 0;
}

function getSiteKey(site) {
  return normalizeSiteKey(site);
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
    .filter(
      (site) =>
        !usedKeys.has(getSiteKey(site)) && !resultKeys.has(getSiteKey(site)),
    )
    .slice(0, limit - result.length);
  supplements.forEach((site) => usedKeys.add(getSiteKey(site)));
  return [...result, ...supplements];
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

function fillCategorySites(sites, limit = 4) {
  return dedupeSites(normalizeList(sites), new Set()).slice(0, limit);
}

function isRequestCanceled(error, signal) {
  return Boolean(signal?.aborted || error?.code === "ERR_CANCELED");
}

function createHomeRequestController() {
  homeRequestController?.abort();
  homeRequestController = new AbortController();
  return homeRequestController;
}

function createCategoryRequestController(parentSignal) {
  categoryRequestController?.abort();
  const controller = new AbortController();
  categoryRequestController = controller;

  if (parentSignal) {
    if (parentSignal.aborted) {
      controller.abort();
    } else {
      parentSignal.addEventListener("abort", () => controller.abort(), {
        once: true,
      });
    }
  }

  return controller;
}

function hasWebsiteData(siteMap = {}) {
  return Object.values(siteMap).some((sites) => normalizeList(sites).length);
}

function getLoadErrorMessage(error) {
  return error?.code === "ECONNABORTED"
    ? "资源加载时间较长，可以稍后重试。"
    : "无法获取热门分类，请检查网络后重试。";
}

async function loadCategorySites(
  categoryList,
  excludeIds = [],
  signal,
  retainedSiteMap = {},
) {
  const nextSiteMap = {};
  const remoteWebsites = [];
  let hasSuccessfulResponse = false;
  let hasRequestError = false;
  loadingCategorySites.value = true;
  try {
    for (let page = 1; page <= 20; page += 1) {
      try {
        const response = await siteAPI.getSites(
          {
            page,
            limit: WEBSITE_PAGE_SIZE,
            page_size: WEBSITE_PAGE_SIZE,
            sort: "recommend",
            exclude_ids: page === 1 ? idsParam(excludeIds) : undefined,
          },
          { signal, timeout: HOME_RESOURCE_TIMEOUT_MS },
        );
        const pageItems = normalizeWebsiteList(response);
        remoteWebsites.push(...pageItems);
        hasSuccessfulResponse = true;
        if (pageItems.length < WEBSITE_PAGE_SIZE) break;
      } catch (requestError) {
        if (isRequestCanceled(requestError, signal)) {
          return {
            map: null,
            websites: [],
            hasSuccessfulResponse,
            hasRequestError,
          };
        }
        hasRequestError = true;
        console.warn(
          "[home] website catalog request failed",
          requestError?.message,
        );
        break;
      }
    }

    if (signal?.aborted) {
      return {
        map: null,
        websites: [],
        hasSuccessfulResponse: false,
        hasRequestError,
      };
    }
    const retainedWebsites = flattenCategorySites(retainedSiteMap);
    const websites = mergeWebsiteLists(retainedWebsites, remoteWebsites);
    const nextCategories = mergeCategoryLists(
      categoryList,
      deriveCategoriesFromWebsites(websites),
    );
    Object.assign(
      nextSiteMap,
      createCategorySitesMap(websites, nextCategories),
    );
    return {
      map: nextSiteMap,
      websites,
      hasSuccessfulResponse,
      hasRequestError,
    };
  } finally {
    if (!signal?.aborted) loadingCategorySites.value = false;
  }
}

async function loadCategoriesLegacy(
  excludeIds = [],
  parentSignal,
  force = false,
) {
  return loadCategories(excludeIds, parentSignal, force);

  const requestId = ++categoryRequestId;
  const controller = createCategoryRequestController(parentSignal);
  const { signal } = controller;
  const retainedCategories = categories.value;
  const retainedSiteMap = categorySitesMap.value;
  const hasExistingData =
    retainedCategories.length > 0 && hasWebsiteData(retainedSiteMap);

  categoryRefreshing.value = hasExistingData;
  categoryError.value = "";
  if (!hasExistingData) categoryStatus.value = "loading";

  const result = await runListRequest(async () => {
    const response = await categoryAPI.getCategories({
      signal,
      timeout: HOME_RESOURCE_TIMEOUT_MS,
      force,
    });
    return unwrapList(response).filter((item) => !item.parent_id);
  });

  if (signal.aborted || requestId !== categoryRequestId) return;

  if (result.status === "error") {
    categoryError.value = getLoadErrorMessage(result.error);
    categoryRefreshing.value = false;
    categoryStatus.value = hasExistingData ? "success" : "error";
    console.warn("[home] category request failed", result.error?.message);
    return;
  }

  if (result.status === "empty") {
    categories.value = [];
    categorySitesMap.value = {};
    categoryStatus.value = "empty";
    categoryRefreshing.value = false;
    return;
  }

  const siteResult = await loadCategorySites(
    result.items,
    excludeIds,
    signal,
    retainedSiteMap,
  );
  if (signal.aborted || requestId !== categoryRequestId || !siteResult?.map) {
    return;
  }

  const hasNextData = hasWebsiteData(siteResult.map);
  if (!siteResult.hasSuccessfulResponse && hasExistingData) {
    categoryRefreshing.value = false;
    categoryStatus.value = "success";
    categoryError.value = "网站资源更新失败，已保留上一次成功数据。";
    console.warn("[home] category resources refresh failed");
    return;
  }

  if (!siteResult.hasSuccessfulResponse && !hasNextData) {
    categories.value = result.items;
    categorySitesMap.value = siteResult.map;
    categoryRefreshing.value = false;
    categoryStatus.value = "error";
    categoryError.value = "无法获取网站资源，请检查网络后重试。";
    console.warn("[home] category resources initial load failed");
    return;
  }

  categories.value = result.items;
  categorySitesMap.value = siteResult.map;
  categoryRefreshing.value = false;
  categoryStatus.value = hasNextData ? "success" : "empty";
  if (siteResult.hasRequestError) {
    categoryError.value = "部分网站资源更新失败，已保留可用数据。";
  }
}

async function loadCategories(excludeIds = [], parentSignal, force = false) {
  void excludeIds;
  const requestId = ++categoryRequestId;
  const controller = createCategoryRequestController(parentSignal);
  const { signal } = controller;
  const retainedCategories = categories.value;
  const retainedSiteMap = categorySitesMap.value;
  const retainedWebsites = flattenCategorySites(retainedSiteMap);

  categoryRefreshing.value = retainedWebsites.length > 0;
  categoryError.value = "";
  if (!retainedWebsites.length) categoryStatus.value = "loading";

  const categoryRequest = runListRequest(async () => {
    const response = await categoryAPI.getCategories({
      signal,
      timeout: HOME_RESOURCE_TIMEOUT_MS,
      force,
    });
    return unwrapList(response).filter((item) => !item.parent_id);
  });
  const websiteRequest = loadCategorySites(
    mergeCategoryLists(retainedCategories, builtinCategories),
    [],
    signal,
    retainedSiteMap,
  );
  const [categoryResult, siteResult] = await Promise.all([
    categoryRequest,
    websiteRequest,
  ]);

  if (signal.aborted || requestId !== categoryRequestId || !siteResult?.map) {
    return;
  }

  const nextWebsites = siteResult.websites?.length
    ? siteResult.websites
    : retainedWebsites;
  const nextCategories = mergeCategoryLists(
    categoryResult.status === "success" ? categoryResult.items : [],
    retainedCategories,
    deriveCategoriesFromWebsites(nextWebsites),
  );

  if (categoryResult.status === "error") {
    categoryError.value = getLoadErrorMessage(categoryResult.error);
    console.warn(
      "[home] category request failed",
      categoryResult.error?.message,
    );
  }
  if (siteResult.hasRequestError) {
    categoryError.value = categoryError.value
      ? `${categoryError.value}；当前保留可用网站数据。`
      : "部分网站资源更新失败，已保留可用数据。";
    console.warn("[home] website catalog refresh partially failed");
  }

  categories.value = nextCategories;
  categorySitesMap.value = siteResult.map;
  categoryRefreshing.value = false;
  categoryStatus.value = nextWebsites.length
    ? "success"
    : categoryResult.status === "error" || siteResult.hasRequestError
      ? "error"
      : "empty";
  if (nextWebsites.length) writeWebsiteCache(nextWebsites);
}

async function retryCategories() {
  const controller = createHomeRequestController();
  await loadCategories(
    siteIds([
      ...marqueeSites.value,
      ...hotSites.value,
      ...favoriteStackSites.value,
    ]),
    controller.signal,
    true,
  );
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

function handleAiAssistantEntry() {
  if (loggedIn.value) {
    aiAssistantStore.openAssistant();
    return;
  }

  goToAiAssistantLogin();
}

function getHomeSiteCollections() {
  return [
    careerSites.value,
    recommended.value,
    hotSites.value,
    marqueeSites.value,
    favoriteStackSites.value,
    currentCommonTools.value,
    latestSites.value,
    ...Object.values(categorySitesMap.value),
  ];
}

function syncFavoriteFlags(sites) {
  return normalizeList(sites).map((site) => {
    if (favoriteStore.hasSnapshot) {
      site.is_favorited = favoriteStore.isFavorite(site);
    }
    return site;
  });
}

function syncAllFavoriteFlags() {
  getHomeSiteCollections().forEach((sites) => {
    syncFavoriteFlags(sites);
  });
}

watch(
  () => favoriteStore.items,
  () => syncAllFavoriteFlags(),
  { deep: true },
);

function clearFavoriteState() {
  favoriteStore.clearFavoriteState();
  getHomeSiteCollections().forEach((sites) => {
    normalizeList(sites).forEach((site) => {
      site.is_favorited = false;
    });
  });
}

async function loadFavoriteState() {
  if (!loggedIn.value) {
    clearFavoriteState();
    return;
  }

  const userId = userStore.userInfo?.id ?? userStore.userInfo?.user_id;
  const restored = favoriteStore.restoreFavoriteCache(userId);
  await favoriteStore.loadFavorites({
    keepExistingData: true,
    background: restored,
  });
  syncAllFavoriteFlags();
}

function visitSite(site) {
  const url = normalizeUrl(site?.url);
  if (url) {
    openVisitedSite(
      { ...site, url },
      {
        source:
          site?.visit_source ||
          (site?.recommend_reason ? "career_recommend" : "home_recommend"),
      },
    );
  } else if (site?.id) {
    router.push(`/site/${site.id}`);
  }
}

function visitGuestCareerSite(site, event) {
  const url = normalizeUrl(site?.url);
  if (!url) return;
  openVisitedSite(
    { ...site, url, external_only: true },
    { source: "guest_career_preview", event },
  );
}

async function requestHotSites({
  excludeCurrent = false,
  preserveOnError = false,
  excludeIds = [],
  targetRef = hotSites,
  signal,
} = {}) {
  hotError.value = "";
  const requestExcludeIds = excludeCurrent
    ? [...excludeIds, ...siteIds(targetRef.value)]
    : excludeIds;
  const exclude_ids = idsParam(requestExcludeIds);

  try {
    const hotRes = await siteAPI.getHot(
      {
        limit: 8,
        ai_only: 1,
        exclude_ids,
      },
      { signal, timeout: 6000 },
    );
    const sites = filterAiResources(normalizeWebsiteList(hotRes));
    if (sites.length || !preserveOnError) {
      targetRef.value = sites;
    }
    if (sites.length) return sites;
  } catch (requestError) {
    if (isRequestCanceled(requestError, signal)) throw requestError;
    hotError.value = "AI 资源更新失败，请稍后重试";
    if (!preserveOnError) {
      targetRef.value = [];
    }
    throw new Error(hotError.value);
  }
}

let latestCareerRequestId = 0;
let latestCareerSelectionId = 0;

function getCareerCode(career = {}) {
  return String(
    career.careerCode || career.career_code || career.code || "",
  ).trim();
}

function ensureCareerSitePool(careerCode, sites = []) {
  const normalizedSites = normalizeCareerSiteList(sites);
  const uniqueSites = [];
  const seenKeys = new Set();

  for (const site of normalizedSites) {
    const key = normalizeSiteKey(site) || `name:${site.name}`;
    if (seenKeys.has(key)) continue;
    seenKeys.add(key);
    uniqueSites.push(
      normalizeCareerSite({
        ...site,
        careerCodes: site.careerCodes?.length ? site.careerCodes : [careerCode],
      }),
    );
    if (uniqueSites.length >= CAREER_SITE_POOL_MAX) break;
  }

  if (import.meta.env.DEV && uniqueSites.length < CAREER_BATCH_SIZE) {
    console.debug("[recommendation] candidate pool is shorter than one batch", {
      careerCode,
      candidate_pool_size: uniqueSites.length,
      batch_size: CAREER_BATCH_SIZE,
    });
  }

  return syncFavoriteFlags(uniqueSites);
}

function mergeCareerSites(careerCode, apiSites = []) {
  const apiSiteList = normalizeCareerSiteList(apiSites);
  // Personalised recommendation cards must always be sourced from the API's
  // database-backed candidate pool.  The backend owns all fallback stages.
  return ensureCareerSitePool(careerCode, apiSiteList);
}

function refreshCareerBatch(event) {
  event?.preventDefault?.();
  event?.stopPropagation?.();

  const careerCode = activeCareerCode.value;
  if (!careerCode || !canRefreshCareerBatch.value) return;
  careerBatchHasChanged.value = true;
  if (careerBatchCount.value <= 1) {
    careerBatchIndex.value = 0;
    batchIndexByCareer.value = {
      ...batchIndexByCareer.value,
      [careerCode]: 0,
    };
    persistCareerCache();
    return;
  }
  const nextIndex = (activeCareerBatchIndex.value + 1) % careerBatchCount.value;
  careerBatchIndex.value = nextIndex;
  batchIndexByCareer.value = {
    ...batchIndexByCareer.value,
    [careerCode]: nextIndex,
  };
  persistCareerCache();
}

function revealCardStyle(index, startDelay = 230) {
  const normalizedIndex = Math.max(Number(index) || 0, 0);
  return {
    "--reveal-delay": `${startDelay + Math.min(normalizedIndex * 35, 350)}ms`,
    "--refresh-delay": `${Math.min(normalizedIndex * 22, 220)}ms`,
  };
}

function normalizeRecommendations(payload = {}) {
  const list = Array.isArray(payload.recommendations)
    ? payload.recommendations
    : Array.isArray(payload.careers)
      ? payload.careers
      : [];
  const nextSitesByCareer = {};
  const normalizedList = [];

  for (const career of list) {
    const code = getCareerCode(career);
    if (!code) continue;
    const rawSites = Array.isArray(career.sites)
      ? career.sites
      : Array.isArray(career.websites)
        ? career.websites
        : Array.isArray(career.recommendedSites)
          ? career.recommendedSites
          : [];
    const normalizedCareer = {
      ...career,
      code,
      careerCode: code,
      careerName: career.careerName || career.label || "",
      label: career.label || career.careerName || "",
      match_score: career.match_score ?? career.score ?? 0,
      reasons: Array.isArray(career.reasons)
        ? career.reasons
        : career.reason
          ? [career.reason]
          : [],
      sites: mergeCareerSites(code, rawSites),
    };
    nextSitesByCareer[code] = syncFavoriteFlags(normalizedCareer.sites);
    normalizedCareer.sites = nextSitesByCareer[code];
    normalizedCareer.websites = nextSitesByCareer[code];
    normalizedList.push(normalizedCareer);
  }

  return { list: normalizedList, sitesByCareer: nextSitesByCareer };
}

async function updateCareerQuery(code) {
  const nextQuery = { ...route.query };
  if (code) nextQuery.career = code;
  else delete nextQuery.career;
  if (String(route.query.career || "") === code) return;
  await router.replace({ query: nextQuery });
}

async function loadCareerRecommendations({ keepExistingData = false } = {}) {
  const requestId = ++latestCareerRequestId;
  const hasExistingData =
    keepExistingData &&
    recommendations.value.length > 0 &&
    activeCareerSitesPool.value.length > 0;

  careerStatus.value = hasExistingData ? "success" : "loading";
  if (!hasExistingData) questionnaireStatus.value = "loading";
  sitesLoading.value = true;
  sitesError.value = "";

  if (!hasExistingData) {
    careerBatchIndex.value = 0;
    batchIndexByCareer.value = {};
    activeCareerCode.value = "";
    sitesByCareer.value = {};
    recommendations.value = [];
    careerAbilityTags.value = [];
    careerInterestTags.value = [];
    questionnaireCompleted.value = Boolean(userStore.questionnaireCompleted);
  }

  if (!loggedIn.value) {
    sitesLoading.value = false;
    careerStatus.value = "idle";
    return;
  }

  try {
    const response = await careerAPI.getRecommendations({ timeout: 10000 });
    if (requestId !== latestCareerRequestId) return;
    const payload = unwrapCareerRecommendationResponse(response);
    const normalized = normalizeRecommendations(payload);
    const hasQuestionnaireStatus = Object.prototype.hasOwnProperty.call(
      payload,
      "questionnaire_completed",
    );
    questionnaireCompleted.value = hasQuestionnaireStatus
      ? Boolean(payload.questionnaire_completed)
      : normalized.list.length > 0 || questionnaireCompleted.value;
    if (hasQuestionnaireStatus && !questionnaireCompleted.value) {
      clearCareerCache();
    }
    const nextQuestionnaireVersion = payload.questionnaire_version
      ? String(payload.questionnaire_version)
      : questionnaireCompleted.value
        ? questionnaireVersion.value || "current"
        : "";
    const questionnaireChanged =
      Boolean(questionnaireVersion.value) &&
      Boolean(nextQuestionnaireVersion) &&
      questionnaireVersion.value !== nextQuestionnaireVersion;
    questionnaireVersion.value = nextQuestionnaireVersion;
    recommendations.value = normalized.list;
    sitesByCareer.value = normalized.sitesByCareer;
    careerAbilityTags.value = Array.isArray(payload.ability_tags)
      ? payload.ability_tags
      : [];
    careerInterestTags.value = Array.isArray(payload.interest_tags)
      ? payload.interest_tags
      : [];

    if (questionnaireChanged) batchIndexByCareer.value = {};
    const nextBatchIndexByCareer = {};
    for (const career of normalized.list) {
      const code = career.careerCode;
      const pool = normalized.sitesByCareer[code] || [];
      const batchCount = getFullCareerBatchCount(pool);
      const requestedIndex = Number(batchIndexByCareer.value[code]) || 0;
      nextBatchIndexByCareer[code] = batchCount
        ? ((requestedIndex % batchCount) + batchCount) % batchCount
        : 0;
    }
    batchIndexByCareer.value = nextBatchIndexByCareer;

    const requestedCareer =
      typeof route.query.career === "string" ? route.query.career : "";
    const validRequestedCareer = normalized.list.some(
      (career) => career.careerCode === requestedCareer,
    );
    const nextCareerCode = validRequestedCareer
      ? requestedCareer
      : normalized.list[0]?.careerCode || "";
    activeCareerCode.value = nextCareerCode;
    careerBatchIndex.value =
      Number(batchIndexByCareer.value[nextCareerCode]) || 0;
    await updateCareerQuery(nextCareerCode);
    questionnaireStatus.value = questionnaireCompleted.value
      ? "ready"
      : "empty";
    careerStatus.value = activeSites.value.length ? "success" : "empty";
    if (import.meta.env.DEV) {
      const activePool = normalized.sitesByCareer[nextCareerCode] || [];
      const activeBatchIndex =
        Number(batchIndexByCareer.value[nextCareerCode]) || 0;
      console.debug("[recommendation] profile:", {
        occupation:
          payload.recommendation_profile?.occupation ||
          payload.profile?.occupation ||
          "",
        career_code:
          payload.recommendation_profile?.career_code || nextCareerCode,
        direction: payload.recommendation_profile?.direction || "",
        primary_need: payload.recommendation_profile?.primary_need || "",
      });
      console.debug("[recommendation] API items:", {
        items: Number(
          payload.candidate_pool_size ??
            payload.items?.length ??
            payload.websites?.length ??
            0,
        ),
        candidate_pool_size: Number(
          payload.candidate_pool_size ?? activePool.length,
        ),
        batch_id: payload.batch_id || "",
        recommendation_session_id: payload.recommendation_session_id || "",
        profile_version: payload.profile_version || "",
        profile_schema_version:
          payload.profile_schema_version || payload.profile_version || "",
      });
      console.debug("[recommendation] candidate pool:", activePool.length);
      console.debug("[recommendation] batch index:", activeBatchIndex);
      console.debug(
        "[recommendation] visible items:",
        Math.max(
          0,
          Math.min(
            CAREER_BATCH_SIZE,
            activePool.length - activeBatchIndex * CAREER_BATCH_SIZE,
          ),
        ),
      );
    }
    persistCareerCache();
  } catch (requestError) {
    if (requestId !== latestCareerRequestId) return;
    if (hasExistingData) {
      careerStatus.value = "success";
      sitesError.value = "推荐更新失败，当前仍显示上次成功加载的结果。";
      errorToast(sitesError.value);
      console.warn(
        "[home] career recommendation revalidation failed",
        requestError?.message,
      );
      return;
    }
    questionnaireStatus.value = "error";
    careerStatus.value = "error";
    sitesError.value = "职业推荐加载失败，请检查后端服务后重试。";
    errorToast(sitesError.value);
    console.warn(
      "[home] career recommendation request failed",
      requestError?.message,
    );
  } finally {
    if (requestId === latestCareerRequestId) sitesLoading.value = false;
  }
}

async function loadSitesForCareer(careerCode) {
  const career = recommendations.value.find(
    (item) => item.careerCode === careerCode,
  );
  if (!career) return;
  sitesByCareer.value = {
    ...sitesByCareer.value,
    [careerCode]: ensureCareerSitePool(careerCode, career.sites || []),
  };
}

async function retryCareerSites() {
  const keepExistingData =
    recommendations.value.length > 0 && activeCareerSitesPool.value.length > 0;
  await loadCareerRecommendations({ keepExistingData });
}

async function selectCareer(career) {
  const careerCode = getCareerCode(career);
  if (
    !careerCode ||
    !recommendations.value.some((item) => item.careerCode === careerCode)
  ) {
    return;
  }
  const selectionId = ++latestCareerSelectionId;
  const isSameCareer = activeCareerCode.value === careerCode;
  activeCareerCode.value = careerCode;
  const rememberedBatchIndex = isSameCareer
    ? Number(batchIndexByCareer.value[careerCode]) || 0
    : 0;
  const safeBatchIndex = careerBatchCount.value
    ? rememberedBatchIndex % careerBatchCount.value
    : 0;
  careerBatchIndex.value = safeBatchIndex;
  batchIndexByCareer.value = {
    ...batchIndexByCareer.value,
    [careerCode]: safeBatchIndex,
  };
  sitesError.value = "";
  const hasCachedSites = Object.prototype.hasOwnProperty.call(
    sitesByCareer.value,
    careerCode,
  );
  sitesLoading.value = !hasCachedSites;
  careerStatus.value = hasCachedSites
    ? activeSites.value.length
      ? "success"
      : "empty"
    : "loading";
  await updateCareerQuery(careerCode);
  if (selectionId !== latestCareerSelectionId) return;
  if (!hasCachedSites) await loadSitesForCareer(careerCode);
  if (selectionId !== latestCareerSelectionId) return;
  sitesLoading.value = false;
  careerStatus.value = activeSites.value.length ? "success" : "empty";
  persistCareerCache();
}

async function loadMarqueeSites(excludeIds = [], signal) {
  try {
    const response = await siteAPI.getRandom(
      {
        limit: 16,
        category: "AI工具",
        scene: "marquee",
        exclude_ids: idsParam(excludeIds),
      },
      { signal, timeout: 6000 },
    );
    return filterAiResources(normalizeWebsiteList(response));
  } catch (requestError) {
    if (isRequestCanceled(requestError, signal)) throw requestError;
    return [];
  }
}

async function loadSupplementaryHomeSites(signal) {
  const usedKeys = new Set(
    featuredWebsites.map((site) => normalizeSiteKey(site)).filter(Boolean),
  );
  const marqueeRes = await loadMarqueeSites([], signal);
  if (signal.aborted) return;
  marqueeSites.value = fillWithFallback(marqueeRes, 16, usedKeys);

  const [hotRes] = await Promise.allSettled([
    requestHotSites({ excludeIds: siteIds(marqueeSites.value), signal }),
  ]);
  if (signal.aborted) return;
  hotSites.value = fillWithFallback(getSettledData(hotRes, []), 8, usedKeys);

  const [favoriteRes] = await Promise.allSettled([
    requestHotSites({
      excludeIds: siteIds([...marqueeSites.value, ...hotSites.value]),
      targetRef: favoriteStackSites,
      signal,
    }),
  ]);
  if (signal.aborted) return;
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
    siteAPI.getRecommend(
      { limit: 8, exclude_ids: excludeForRest },
      { signal, timeout: 6000 },
    ),
    siteAPI.getLatest({ limit: 12 }, { signal, timeout: 6000 }),
  ]);
  if (signal.aborted) return;

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
}

async function loadHome() {
  loading.value = true;
  error.value = "";
  const controller = createHomeRequestController();
  const { signal } = controller;
  try {
    void loadCategories([], signal);
    void loadSupplementaryHomeSites(signal).catch((requestError) => {
      if (!isRequestCanceled(requestError, signal)) {
        console.warn(
          "[home] supplementary resources failed",
          requestError?.message,
        );
      }
    });
  } finally {
    loading.value = false;
  }
}

function getHomeScreens() {
  if (!homeMainRef.value) return [];
  return Array.from(homeMainRef.value.querySelectorAll(".home-screen"));
}

function getHomeHeaderOffset() {
  if (!homeMainRef.value) return 0;
  const value = Number.parseFloat(
    window
      .getComputedStyle(homeMainRef.value)
      .getPropertyValue("--home-header-offset"),
  );
  return Number.isFinite(value) ? value : 0;
}

function syncCurrentSectionIndex() {
  const sections = getHomeScreens();
  if (!sections.length) {
    currentSectionIndex.value = 0;
    return;
  }

  const anchorTop = window.scrollY <= 10 ? 0 : getHomeHeaderOffset();
  let closestIndex = 0;
  let closestDistance = Number.POSITIVE_INFINITY;
  sections.forEach((section, index) => {
    const distance = Math.abs(section.getBoundingClientRect().top - anchorTop);
    if (distance < closestDistance) {
      closestDistance = distance;
      closestIndex = index;
    }
  });
  currentSectionIndex.value = closestIndex;
}

function updateCurrentSectionFromIntersections() {
  const sections = getHomeScreens();
  let nextIndex = -1;
  let largestRatio = 0;
  sections.forEach((section, index) => {
    const ratio = homeScreenIntersectionRatios.get(section) || 0;
    if (ratio > largestRatio) {
      largestRatio = ratio;
      nextIndex = index;
    }
  });

  if (nextIndex >= 0 && largestRatio >= 0.5) {
    currentSectionIndex.value = nextIndex;
  }
}

function observeHomeScreens() {
  const sections = getHomeScreens();
  if (!("IntersectionObserver" in window)) {
    syncCurrentSectionIndex();
    return;
  }

  if (!homeScreenObserver) {
    homeScreenObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          homeScreenIntersectionRatios.set(
            entry.target,
            entry.isIntersecting ? entry.intersectionRatio : 0,
          );
        });
        updateCurrentSectionFromIntersections();
      },
      { threshold: [0.5, 0.6, 0.75] },
    );
  }

  observedHomeScreens.forEach((section) => {
    if (sections.includes(section)) return;
    homeScreenObserver.unobserve(section);
    observedHomeScreens.delete(section);
    homeScreenIntersectionRatios.delete(section);
  });

  sections.forEach((section) => {
    if (observedHomeScreens.has(section)) return;
    observedHomeScreens.add(section);
    homeScreenObserver.observe(section);
  });
}

function observeCommonToolsSection() {
  const section = commonToolsSectionRef.value;
  if (!section) {
    commonToolsObserver?.disconnect();
    commonToolsObserver = null;
    observedCommonToolsSection = null;
    commonToolsSectionVisible.value = false;
    return;
  }
  if (section === observedCommonToolsSection) return;

  commonToolsObserver?.disconnect();
  observedCommonToolsSection = section;
  commonToolsSectionVisible.value = false;

  if (!("IntersectionObserver" in window)) {
    if (!currentCommonTools.value.length) showNextCommonToolsBatch();
    return;
  }

  commonToolsObserver = new IntersectionObserver(
    ([entry]) => {
      const isVisible = Boolean(
        entry?.isIntersecting &&
        entry.intersectionRatio >= COMMON_TOOLS_ENTER_RATIO,
      );
      if (isVisible === commonToolsSectionVisible.value) return;
      commonToolsSectionVisible.value = isVisible;
      if (isVisible) showNextCommonToolsBatch();
    },
    { threshold: [0, COMMON_TOOLS_ENTER_RATIO] },
  );
  commonToolsObserver.observe(section);
}

function normalizeWheelDelta(event) {
  if (event.deltaMode === WheelEvent.DOM_DELTA_LINE) return event.deltaY * 16;
  if (event.deltaMode === WheelEvent.DOM_DELTA_PAGE)
    return event.deltaY * window.innerHeight;
  return event.deltaY;
}

function isNativeWheelOverlay(target) {
  return (
    target instanceof Element && !!target.closest(HOME_NATIVE_WHEEL_SELECTOR)
  );
}

function canNestedScrollerConsumeWheel(target, deltaY) {
  let element =
    target instanceof HTMLElement ? target : target?.parentElement || null;
  while (
    element &&
    element !== homeMainRef.value &&
    element !== document.body
  ) {
    const style = window.getComputedStyle(element);
    const scrollable =
      /(auto|scroll|overlay)/.test(style.overflowY) &&
      element.scrollHeight > element.clientHeight + 1;
    if (scrollable) {
      if (deltaY > 0) {
        return (
          element.scrollTop + element.clientHeight < element.scrollHeight - 1
        );
      }
      return element.scrollTop > 1;
    }
    element = element.parentElement;
  }
  return false;
}

function easeInOutCubic(progress) {
  return progress < 0.5
    ? 4 * progress * progress * progress
    : 1 - Math.pow(-2 * progress + 2, 3) / 2;
}

function cancelHomePageScroll() {
  window.cancelAnimationFrame(homeScrollAnimationFrame);
  window.cancelAnimationFrame(homeSnapRestoreFrame);
  window.cancelAnimationFrame(homeSnapRestoreSecondFrame);
  homeScrollAnimationFrame = 0;
  homeSnapRestoreFrame = 0;
  homeSnapRestoreSecondFrame = 0;
  document.documentElement.classList.remove("home-page-scrolling");
  homeScrollLocked = false;
}

function finishHomePageScroll(targetIndex, targetY) {
  homeScrollAnimationFrame = 0;
  window.scrollTo(0, targetY);
  currentSectionIndex.value = targetIndex;

  // Let the exact final scroll position paint before restoring mandatory snap.
  homeSnapRestoreFrame = window.requestAnimationFrame(() => {
    homeSnapRestoreFrame = 0;
    homeSnapRestoreSecondFrame = window.requestAnimationFrame(() => {
      homeSnapRestoreSecondFrame = 0;
      document.documentElement.classList.remove("home-page-scrolling");
      homeScrollLocked = false;
      syncCurrentSectionIndex();
    });
  });
}

function animateHomePageScroll(targetSection, targetIndex) {
  homeScrollLocked = true;
  document.documentElement.classList.add("home-page-scrolling");

  const startY = window.scrollY;
  const headerOffset = getHomeHeaderOffset();
  const documentTargetY =
    targetSection.getBoundingClientRect().top + startY - headerOffset;
  const maxScrollY = Math.max(
    0,
    document.documentElement.scrollHeight - window.innerHeight,
  );
  const targetY = Math.min(maxScrollY, Math.max(0, documentTargetY));
  const distance = targetY - startY;
  const reducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  if (reducedMotion || Math.abs(distance) < 1) {
    finishHomePageScroll(targetIndex, targetY);
    return;
  }

  const startTime = window.performance.now();
  const animate = (now) => {
    const progress = Math.min((now - startTime) / HOME_SCROLL_DURATION_MS, 1);
    const nextY = startY + distance * easeInOutCubic(progress);
    window.scrollTo(0, nextY);

    if (progress < 1) {
      homeScrollAnimationFrame = window.requestAnimationFrame(animate);
      return;
    }

    finishHomePageScroll(targetIndex, targetY);
  };

  homeScrollAnimationFrame = window.requestAnimationFrame(animate);
}

function handleHomeWheel(event) {
  if (!window.matchMedia(HOME_DESKTOP_SCROLL_QUERY).matches) return;
  if (event.defaultPrevented || event.ctrlKey || event.shiftKey) return;
  if (Math.abs(event.deltaX) > Math.abs(event.deltaY)) return;

  const deltaY = normalizeWheelDelta(event);
  if (isNativeWheelOverlay(event.target)) return;

  if (homeScrollLocked) {
    event.preventDefault();
    return;
  }

  if (canNestedScrollerConsumeWheel(event.target, deltaY)) return;

  event.preventDefault();
  if (Math.abs(deltaY) < HOME_WHEEL_THRESHOLD) return;

  const sections = getHomeScreens();
  if (!sections.length) return;
  syncCurrentSectionIndex();
  const direction = deltaY > 0 ? 1 : -1;
  const nextIndex = Math.min(
    sections.length - 1,
    Math.max(0, currentSectionIndex.value + direction),
  );
  if (nextIndex === currentSectionIndex.value) return;

  animateHomePageScroll(sections[nextIndex], nextIndex);
}

function scheduleHomeSectionSync() {
  window.cancelAnimationFrame(homeSectionSyncFrame);
  homeSectionSyncFrame = window.requestAnimationFrame(() => {
    observeHomeScreens();
    syncCurrentSectionIndex();
  });
}

function handleHomeViewportResize() {
  cancelHomePageScroll();
  scheduleHomeSectionSync();
}

function updateScrollHintVisibility() {
  isScrollHintVisible.value = window.scrollY <= 10;
}

onMounted(async () => {
  document.documentElement.classList.add("home-scroll-snap");
  updateScrollHintVisibility();
  window.addEventListener("scroll", updateScrollHintVisibility, {
    passive: true,
  });
  window.addEventListener("wheel", handleHomeWheel, { passive: false });
  window.addEventListener("resize", handleHomeViewportResize, {
    passive: true,
  });
  restoreImmediateData();
  restoreCareerCache();
  const careerInitialization = initializeCareerRecommendations();
  await nextTick();
  observeHomeScreens();
  observeCommonToolsSection();
  syncCurrentSectionIndex();

  await loadHome();
  await loadFavoriteState();
  await careerInitialization;
  if (!careerInitializationIdentity) await initializeCareerRecommendations();
  await nextTick();
  observeHomeScreens();
  observeCommonToolsSection();
  syncCurrentSectionIndex();
  observeCareerLayout();
  scheduleCareerLayoutMeasurement({ reset: true });
});

onUpdated(async () => {
  await nextTick();
  observeCommonToolsSection();
  scheduleHomeSectionSync();
});

onBeforeUnmount(() => {
  cancelHomePageScroll();
  document.documentElement.classList.remove("home-scroll-snap");
  window.removeEventListener("scroll", updateScrollHintVisibility);
  window.removeEventListener("wheel", handleHomeWheel);
  window.removeEventListener("resize", handleHomeViewportResize);
  window.cancelAnimationFrame(homeSectionSyncFrame);
  homeScreenObserver?.disconnect();
  homeScreenObserver = null;
  commonToolsObserver?.disconnect();
  commonToolsObserver = null;
  observedCommonToolsSection = null;
  observedHomeScreens.clear();
  homeScreenIntersectionRatios.clear();
  homeRequestController?.abort();
  homeRequestController = null;
  categoryRequestController?.abort();
  categoryRequestController = null;
  categoryRequestId += 1;
  careerLayoutResizeObserver?.disconnect();
  careerLayoutResizeObserver = null;
  window.cancelAnimationFrame(careerLayoutFrame);
  careerLayoutMeasureToken += 1;
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: transparent;
}

.home-main {
  --home-header-offset: 56px;

  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0;
}

.home-screen {
  position: relative;
  scroll-snap-align: start;
  scroll-snap-stop: normal;
}

:global(html.home-scroll-snap) {
  scroll-behavior: auto;
  scroll-snap-type: y proximity;
}

.home-first-screen {
  display: grid;
  min-height: 100vh;
  min-height: 100svh;
  grid-template-rows: minmax(0, 1fr) auto;
  box-sizing: border-box;
  padding: 96px 0 28px;
}

.hero-content {
  min-width: 0;
  min-height: 0;
}

.home-scroll-hint {
  display: inline-flex;
  align-items: center;
  justify-self: center;
  gap: 8px;
  margin: 0;
  color: var(--app-text-muted);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.5;
  opacity: 1;
  text-align: center;
  visibility: visible;
  transition:
    opacity 250ms ease,
    visibility 0s linear;
}

.home-scroll-hint--hidden {
  opacity: 0;
  pointer-events: none;
  visibility: hidden;
  transition-delay: 0ms, 250ms;
}

.home-scroll-hint span {
  font-size: 16px;
  line-height: 1;
}

.home-state {
  width: min(var(--container), calc(100% - 40px));
  margin: 80px auto;
}

.career-recommendation-section {
  padding: 42px 0 38px;
  background: var(--app-page-bg);
}

.career-recommendation-layout {
  display: grid;
  width: min(var(--container), calc(100% - 40px));
  margin: 0 auto;
  grid-template-columns: minmax(270px, 330px) minmax(0, 1fr);
  gap: 28px;
  align-items: start;
}

.career-profile-panel {
  display: grid;
  min-width: 0;
  gap: 18px;
  border: 1px solid var(--app-border);
  border-radius: 24px;
  background: var(--app-card-bg);
  backdrop-filter: blur(var(--app-blur));
  padding: 24px;
  box-shadow: var(--app-card-shadow);
}

.career-profile-panel__header {
  display: grid;
  gap: 9px;
}

.career-profile-panel__header h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: 24px;
  line-height: 1.25;
}

.career-profile-panel__header p,
.career-profile-panel__empty {
  margin: 0;
  color: var(--color-text);
  line-height: 1.65;
}

.career-tag-groups {
  display: grid;
  gap: 14px;
}

.career-tag-group {
  display: grid;
  gap: 8px;
}

.career-tag-group > span {
  color: var(--color-muted);
  font-size: 12px;
  font-weight: 800;
}

.career-tag-group > div {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.career-tag-group b {
  border-radius: 999px;
  background: var(--color-soft-orange);
  color: var(--color-heading);
  padding: 5px 8px;
  font-size: 12px;
  font-weight: 750;
}

.career-selection {
  display: grid;
  min-width: 0;
  gap: 10px;
}

.career-selection h3 {
  margin: 0;
  color: var(--color-muted);
  font-size: 13px;
  font-weight: 800;
  line-height: 1.4;
}

.career-options {
  display: grid;
  min-height: 0;
  align-content: start;
  gap: 8px;
}

.career-option {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  min-height: 50px;
  align-items: center;
  gap: 10px;
  width: 100%;
  border: 1px solid #e3e6ea;
  border-radius: 14px;
  background: var(--app-card-bg);
  padding: 10px 12px;
  color: var(--color-heading);
  text-align: left;
  cursor: pointer;
  font: inherit;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease;
}

.career-option:hover,
.career-option:focus-visible {
  border-color: rgba(17, 24, 39, 0.35);
  background: var(--app-card-hover-bg);
}

.career-option:focus-visible {
  outline: 2px solid rgba(17, 24, 39, 0.18);
  outline-offset: 2px;
}

.career-option.career-option--active,
.career-option.career-option--active:hover,
.career-option.career-option--active:focus-visible {
  border-color: #111827;
  background: var(--app-card-bg);
  box-shadow: inset 0 0 0 1px #111827;
  outline: none;
}

.career-option__main {
  min-width: 0;
}

.career-option__main strong {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.career-option__score {
  color: var(--color-primary-dark);
  white-space: nowrap;
}

.career-profile-panel__link,
.career-profile-panel__action {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-primary-dark);
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  text-decoration: none;
  cursor: pointer;
}

.career-profile-panel__action {
  background: var(--color-primary);
  color: #ffffff;
}

.career-results {
  display: grid;
  min-width: 0;
  gap: 24px;
}

.career-results__heading {
  display: grid;
  gap: 10px;
}

.career-results__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.career-refresh-button {
  display: inline-flex;
  min-height: 36px;
  flex: 0 0 auto;
  align-items: center;
  gap: 7px;
  border: 1px solid rgba(255, 112, 88, 0.28);
  border-radius: 10px;
  background: #fff8f5;
  color: var(--color-primary-dark);
  padding: 8px 12px;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition:
    border-color 180ms ease,
    background-color 180ms ease,
    transform 180ms ease;
}

.career-refresh-button:hover:not(:disabled),
.career-refresh-button:focus-visible {
  border-color: var(--color-primary);
  background: #fff0eb;
  transform: translateY(-1px);
}

.career-refresh-button:focus-visible {
  outline: 3px solid rgba(255, 112, 88, 0.18);
  outline-offset: 2px;
}

.career-refresh-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.career-results__heading h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(28px, 3.4vw, 42px);
  line-height: 1.14;
}

.career-results__heading p {
  margin: 0;
  color: var(--color-text);
  line-height: 1.7;
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

.career-site-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-auto-rows: auto;
  align-items: stretch;
  gap: 20px;
}

.career-site-grid :deep(.site-card-reveal) {
  height: 100%;
}

.career-site-grid :deep(.site-card-reveal:not(.reveal-child)) {
  opacity: 1;
  visibility: visible;
  transform: none;
  transition: none;
  pointer-events: auto;
}

.career-request-state {
  display: grid;
  min-height: 230px;
  place-items: center;
  align-content: center;
  gap: 10px;
  border: 1px dashed var(--color-border);
  border-radius: 22px;
  background: var(--app-card-bg);
  padding: 30px;
  color: var(--color-text);
  text-align: center;
}

.career-request-state > span {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 16px;
  background: var(--color-soft-orange);
  color: var(--color-primary);
  font-size: 22px;
  font-weight: 900;
}

.career-request-state strong {
  color: var(--color-heading);
  font-size: 18px;
}

.career-request-state p {
  margin: 0;
  line-height: 1.6;
}

.career-skeleton-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: stretch;
  gap: 20px;
}

.career-skeleton-card {
  display: grid;
  min-height: 210px;
  align-content: start;
  gap: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--app-card-bg);
  padding: 20px;
}

.career-skeleton-card span,
.career-skeleton-card b,
.career-skeleton-card i {
  display: block;
  border-radius: 10px;
  background: linear-gradient(90deg, #f0f1f3 25%, #fafafa 50%, #f0f1f3 75%);
  background-size: 200% 100%;
  animation: career-skeleton 1.2s ease-in-out infinite;
}

.career-skeleton-card span {
  width: 48px;
  height: 48px;
}

.career-skeleton-card b {
  width: 72%;
  height: 18px;
}

.career-skeleton-card i {
  width: 100%;
  height: 70px;
}

@keyframes career-skeleton {
  to {
    background-position: -200% 0;
  }
}

.ai-login-prompt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin: 28px 0 0;
  border: 1px solid var(--app-card-border);
  border-radius: 16px;
  background: var(--app-card-bg);
  box-shadow: var(--app-card-shadow);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
  padding: 20px 24px;
}

.career-section-cta {
  width: min(var(--container), calc(100% - 40px));
  margin: 28px auto 0;
}

.ai-login-prompt__content {
  min-width: 0;
}

.ai-login-prompt__title {
  margin: 0 0 6px;
  color: var(--app-text-primary);
  font-size: 16px;
  font-weight: 850;
}

.ai-login-prompt__description {
  margin: 0;
  color: var(--app-text-secondary);
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
  .home-first-screen {
    padding: 88px 0 22px;
  }

  .home-scroll-hint {
    max-width: calc(100% - 32px);
    font-size: 12px;
  }

  .home-state {
    width: min(100% - 28px, var(--container));
    margin: 56px auto;
  }
}

@media (min-width: 768px) and (max-width: 1199px) {
  .career-recommendation-layout {
    grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
    gap: 20px;
  }

  .career-site-grid,
  .career-skeleton-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .career-recommendation-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .career-site-grid,
  .career-skeleton-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .career-results__title-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .career-recommendation-layout {
    width: min(100% - 28px, var(--container));
  }

  .ai-login-prompt {
    align-items: stretch;
    flex-direction: column;
    gap: 16px;
    padding: 18px;
  }

  .career-section-cta {
    width: min(100% - 28px, var(--container));
  }

  .ai-login-prompt__button {
    width: 100%;
  }
}

@media (min-width: 1024px) {
  :global(html.home-scroll-snap) {
    --home-header-offset: 56px;

    scroll-behavior: auto;
    scroll-padding-top: var(--home-header-offset);
    scroll-snap-type: y mandatory;
  }

  :global(html.home-scroll-snap.home-page-scrolling) {
    scroll-snap-type: none;
  }

  .home-screen {
    min-height: calc(100vh - var(--home-header-offset));
    min-height: calc(100svh - var(--home-header-offset));
    box-sizing: border-box;
    scroll-margin-top: 0;
    scroll-snap-align: start;
    scroll-snap-stop: always;
  }

  .hero-screen {
    min-height: 100vh;
    min-height: 100svh;
    scroll-margin-top: 0;
  }

  .hero-content {
    transform: translateY(-50px);
  }

  .career-screen {
    display: grid;
    align-content: center;
    padding: 22px 0 18px;
  }

  .career-recommendation-layout {
    max-height: calc(100svh - var(--home-header-offset) - 154px);
    grid-template-columns: minmax(260px, 28%) minmax(0, 1fr);
    align-items: stretch;
    gap: 24px;
  }

  .career-profile-panel,
  .career-results {
    max-height: calc(100svh - var(--home-header-offset) - 154px);
  }

  .career-profile-panel {
    display: flex;
    min-height: 0;
    flex-direction: column;
    overflow: hidden;
  }

  .career-selection {
    min-height: 0;
    flex: 1 1 auto;
    grid-template-rows: auto minmax(0, 1fr);
  }

  .career-options {
    max-height: clamp(220px, 39svh, 340px);
    overflow-y: auto;
    overscroll-behavior: contain;
    padding-right: 4px;
    scrollbar-gutter: stable;
    scrollbar-color: rgba(100, 116, 139, 0.28) transparent;
    scrollbar-width: thin;
  }

  .career-options::-webkit-scrollbar {
    width: 6px;
  }

  .career-options::-webkit-scrollbar-track {
    background: transparent;
  }

  .career-options::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: rgba(100, 116, 139, 0.24);
  }

  .career-options:hover::-webkit-scrollbar-thumb {
    background: rgba(100, 116, 139, 0.4);
  }

  .career-results {
    min-height: 0;
    align-content: start;
    gap: 16px;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding-right: 4px;
    scrollbar-gutter: stable;
  }

  .career-site-grid,
  .career-skeleton-grid {
    gap: 16px;
  }

  .career-section-cta {
    margin-top: 16px;
  }

  .popular-screen {
    display: grid;
    grid-template-rows: minmax(0, 1fr) auto;
    align-items: stretch;
  }

  .popular-screen :deep(.recommend-section) {
    align-self: center;
    padding: 20px 0 24px;
  }

  .popular-screen :deep(.recommend-heading) {
    margin-bottom: 18px;
  }

  .popular-screen :deep(.recommend-grid) {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .popular-screen :deep(.brand-marquee__viewport) {
    padding: 14px 0;
  }

  .category-screen {
    display: grid;
    height: calc(100vh - var(--home-header-offset));
    height: calc(100svh - var(--home-header-offset));
    align-items: center;
    overflow: hidden;
    padding: 4px 0 44px;
  }

  .category-screen :deep(.category-section) {
    height: 100%;
    min-height: 0;
    grid-template-rows: auto auto minmax(0, 1fr);
    gap: 14px;
  }

  .favorite-screen {
    display: grid;
    place-items: center;
  }

  .favorite-screen :deep(.favorite-band) {
    width: 100%;
    margin-top: 0;
    padding: 32px 0;
  }
}

@media (min-width: 1024px) and (max-width: 1199px) {
  .career-site-grid,
  .career-skeleton-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (prefers-reduced-motion: reduce) {
  .career-skeleton-card span,
  .career-skeleton-card b,
  .career-skeleton-card i {
    animation: none;
  }
}
</style>
