<template>
  <div
    id="app-root"
    :class="{ 'ai-assistant-open': aiAssistantStore.isOpen }"
  >
    <AppHeader v-if="showAppHeader" />
    <main
      class="app-route-content"
      :class="{
        'app-route-content--header-clearance':
          showAppHeader && route.name !== 'Home',
      }"
    >
      <RouterView v-slot="{ Component }">
        <Transition name="route-page">
          <component :is="Component" :key="routeViewKey" />
        </Transition>
      </RouterView>
    </main>
    <RecommendationPreferencePanel compact />
    <AiSiteAssistant @visit="visitAiRecommendation" />
  </div>
  <transition name="slide-up">
    <div v-if="showConsent" class="cookie-banner block-shadow">
      <div class="cookie-content">
        <span class="cookie-icon">🍪</span>
        <p>
          我们使用 Cookie
          来提升您的浏览体验、分析网站流量并提供个性化内容。继续使用即表示您同意我们的<router-link
            to="/privacy"
            >隐私政策</router-link
          >。
        </p>
      </div>
      <div class="cookie-actions">
        <button class="btn-cancel" @click="handleConsent('rejected')">
          仅必要
        </button>
        <button class="btn-primary" @click="handleConsent('accepted')">
          接受全部
        </button>
      </div>
    </div>
  </transition>
  <QuestionnaireModal
    :visible="userStore.questionnaireModalVisible"
    @dismiss="userStore.dismissQuestionnaireModal"
  />
  <ToastNotification
    :message="toast.message"
    :type="toast.type"
    @dismiss="toast.message = ''"
  />
  <div v-if="personalizationStore.conflict" class="personalization-conflict" role="dialog" aria-modal="true" aria-labelledby="personalization-conflict-title">
    <section>
      <h2 id="personalization-conflict-title">检测到本机个性化设置</h2>
      <p>当前浏览器和账户中保存了不同主题设置。请选择登录后使用哪一套。你的选择会被记住，之后相同情况将自动处理。</p>
      <div><button type="button" class="btn-cancel" @click="personalizationStore.useAccountSettings">使用账户设置</button><button type="button" class="btn-primary" @click="syncGuest">将当前设置保存到账户</button></div>
    </section>
  </div>
  <ClickSpark
    color-mode="auto"
    :spark-size="15"
    :spark-radius="60"
    :spark-count="11"
    :duration="500"
    :extra-scale="0.9"
  />
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ToastNotification from "./components/ToastNotification.vue";
import RecommendationPreferencePanel from "./components/site/RecommendationPreferencePanel.vue";
import AiSiteAssistant from "./components/ai/AiSiteAssistant.vue";
import AppHeader from "./components/layout/AppHeader.vue";
import ClickSpark from "./components/effects/ClickSpark.vue";
import QuestionnaireModal from "./components/questionnaire/QuestionnaireModal.vue";
import { useUserStore } from "./stores/user";
import { usePersonalizationStore } from "./stores/personalization";
import { useAiAssistantStore } from "./stores/aiAssistant";
import { normalizeUrl } from "./utils/api";
import { visitSite as openVisitedSite } from "./utils/siteVisit";

const showConsent = ref(false);
const toast = reactive({ message: "", type: "info" });
const userStore = useUserStore();
const personalizationStore = usePersonalizationStore();
const aiAssistantStore = useAiAssistantStore();
const route = useRoute();
const router = useRouter();
const headerRouteNames = new Set([
  "Home",
  "SiteDetail",
  "SearchResults",
  "Favorites",
  "Questionnaire",
  "Profile",
  "ProfileSection",
  "Personalization",
]);
const showAppHeader = computed(() => headerRouteNames.has(route.name));
const routeViewKey = computed(() =>
  ["Profile", "ProfileSection"].includes(route.name)
    ? "profile-layout"
    : route.fullPath,
);

function handleToast(event) {
  toast.message = "";
  requestAnimationFrame(() => {
    toast.type = event.detail?.type || "info";
    toast.message = event.detail?.message || "";
  });
}

onMounted(() => {
  if (!localStorage.getItem("cookie_consent_status")) {
    showConsent.value = true;
  }
  window.addEventListener("app-toast", handleToast);
  userStore.checkQuestionnaireStatus({ open: true });
  personalizationStore.load().catch(() => {});
});

watch(
  () => route.path,
  (path) => {
    personalizationStore.apply(personalizationStore.settings, { disabled: path.startsWith("/admin") });
    if (path === "/" || path === "/personalization" || path === "/profile/personalization") personalizationStore.retryPendingBackgroundSync({ quiet: true });
  },
  { immediate: true },
);

watch(
  () => [userStore.isLoggedIn, userStore.userInfo?.id || userStore.userInfo?.username],
  ([loggedIn, userId], previous) => {
    personalizationStore.handleAuthTransition({ loggedIn, userId }).catch(() => {});
    if (!loggedIn || !userId) {
      userStore.resetQuestionnaireState();
      return;
    }
    if (!previous || loggedIn !== previous[0] || userId !== previous[1]) {
      userStore.checkQuestionnaireStatus({ open: true });
    }
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  window.removeEventListener("app-toast", handleToast);
});

const handleConsent = (status) => {
  localStorage.setItem("cookie_consent_status", status);
  showConsent.value = false;
};

async function syncGuest() {
  await personalizationStore.syncGuestToAccount();
}

function visitAiRecommendation(site) {
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
    return;
  }

  if (site?.id) router.push(`/site/${site.id}`);
}
</script>

<style scoped>
.cookie-banner {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: min(90%, 680px);
  z-index: 99999;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 16px 18px 16px 22px;
  color: var(--mono-text);
  background: #ffffff !important;
  border: 1px solid var(--mono-border);
  border-radius: var(--mono-radius-lg);
  box-shadow: var(--mono-shadow-md);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}
.personalization-conflict { position: fixed; z-index: 100000; inset: 0; display: grid; place-items: center; padding: 20px; background: #ffffff; }
.personalization-conflict section { width: min(100%, 520px); padding: 26px; border: 1px solid #e8edf3; border-radius: 20px; color: var(--color-heading); background: #fff; box-shadow: 0 10px 30px rgba(15,23,42,.08); }
.personalization-conflict h2 { margin: 0 0 10px; }.personalization-conflict p { line-height: 1.65; }.personalization-conflict section > div { display: flex; gap: 10px; justify-content: flex-end; }
.cookie-content {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 13px;
  line-height: 1.6;
}
.cookie-content p {
  margin: 0;
  color: var(--mono-text-soft);
}
.cookie-icon {
  filter: grayscale(1);
}
.cookie-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translate(-50%, 50px);
}
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.5s var(--mono-ease);
}

@media (max-width: 680px) {
  .cookie-banner {
    align-items: stretch;
    flex-direction: column;
  }
  .cookie-actions {
    width: 100%;
  }
  .cookie-actions button {
    flex: 1;
  }
}
</style>

<style>
body {
  margin: 0;
  padding: 0;
}
/* 强制显示垂直滚动条，彻底杜绝因滚动条时隐时现导致的页面左右晃动 */
html {
  overflow-y: scroll;
  scrollbar-gutter: stable;
}

.app-route-content {
  position: relative;
  min-height: 100vh;
}

.app-route-content--header-clearance {
  min-height: calc(100vh - var(--app-route-content-top));
  padding-top: var(--app-route-content-top);
}

.app-route-content--header-clearance > .page {
  min-height: calc(100vh - var(--app-route-content-top));
}

.route-page-enter-active {
  transition:
    opacity 400ms cubic-bezier(0.22, 1, 0.36, 1),
    transform 400ms cubic-bezier(0.22, 1, 0.36, 1);
}

.route-page-leave-active {
  position: absolute;
  z-index: 0;
  inset: 0;
  width: 100%;
  pointer-events: none;
  transition:
    opacity 220ms ease,
    transform 220ms ease;
}

.route-page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.route-page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (prefers-reduced-motion: reduce) {
  .route-page-enter-active,
  .route-page-leave-active {
    transition: none;
  }
}
</style>
