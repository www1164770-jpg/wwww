<template>
  <div class="ai-site-assistant">
    <button
      type="button"
      class="ai-site-assistant__launcher"
      v-show="!isOpen"
      aria-label="打开知航AI助手"
      :aria-expanded="isOpen"
      aria-controls="ai-site-assistant-panel"
      @click="handleLauncher"
    >
      <Bot aria-hidden="true" />
      <span>AI<br />助手</span>
      <ChevronLeft class="ai-site-assistant__launcher-arrow" aria-hidden="true" />
    </button>

    <transition name="ai-drawer">
      <div
        v-if="isOpen"
        class="ai-site-assistant__overlay"
        @click.self="closeAssistant"
      >
      <aside
        id="ai-site-assistant-panel"
        class="ai-site-assistant__panel"
        role="dialog"
        aria-modal="false"
        aria-labelledby="ai-site-assistant-title"
      >
        <header class="ai-site-assistant__header">
          <div class="ai-site-assistant__header-copy">
            <span class="ai-site-assistant__header-icon" aria-hidden="true">
              <Sparkles />
            </span>
            <div>
              <h2 id="ai-site-assistant-title">知航AI助手</h2>
              <p class="ai-site-assistant__eyebrow">你的学习与工作智能伙伴</p>
            </div>
          </div>
          <div class="ai-site-assistant__header-actions">
            <button
              type="button"
              class="ai-site-assistant__minimize"
              aria-label="最小化知航AI助手"
              @click="closeAssistant"
            >
              <Minus aria-hidden="true" />
            </button>
          <button
            type="button"
            class="ai-site-assistant__close"
            aria-label="关闭知航AI助手"
            @click="closeAssistant"
          >
            ×
          </button>
          </div>
        </header>

        <nav class="ai-site-assistant__tabs" aria-label="AI助手功能">
          <button type="button" disabled aria-disabled="true">
            <MessageCircle aria-hidden="true" />
            <span>对话</span>
          </button>
          <button type="button" class="is-active" aria-current="page">
            <Search aria-hidden="true" />
            <span>推荐</span>
          </button>
          <button type="button" disabled aria-disabled="true">
            <FileText aria-hidden="true" />
            <span>写作</span>
          </button>
        </nav>

        <div class="ai-site-assistant__body">
          <section v-if="status === 'initial'" class="ai-site-assistant__welcome">
            <h3>👋 你好！我是知航AI助手</h3>
            <p>
              我可以帮你查找资源、解答问题、提供学习建议，也可以协助你梳理思路。请告诉我你的需求吧！
            </p>
          </section>

          <section class="ai-site-assistant__examples" aria-label="示例需求">
            <div class="ai-site-assistant__examples-heading">
              <strong>你可以这样问：</strong>
              <span class="ai-site-assistant__refresh" aria-disabled="true">
                <RefreshCw aria-hidden="true" /> 换一批
              </span>
            </div>
            <button
              v-for="example in examples"
              :key="example"
              type="button"
              :disabled="isLoading"
              @click="fillExample(example)"
            >
              <span>{{ example }}</span>
              <ArrowRight aria-hidden="true" />
            </button>
          </section>

          <p
            v-if="status === 'loading'"
            class="ai-site-assistant__status"
            aria-live="polite"
          >
            正在从平台网站中为你筛选……
          </p>

          <section v-if="understanding.conditions.length" class="ai-site-assistant__reason" aria-label="已理解的需求">
            <strong>已理解的需求</strong>
            <span v-for="(item, index) in understanding.conditions" :key="index">
              {{ item.strength === 'must' ? '必须' : '偏好' }} · {{ item.label }}（{{ item.evidence }}）
            </span>
          </section>
          <p v-if="understanding.notice" class="ai-site-assistant__status" aria-live="polite">{{ understanding.notice }}</p>
          <p v-for="message in understanding.clarifications" :key="message" class="ai-site-assistant__feedback">{{ message }}</p>
          <p v-if="understanding.degraded" class="ai-site-assistant__status">智能理解暂不可用或检索已降级，请核对以下条件和资源信息。</p>

          <p
            v-if="status === 'empty'"
            class="ai-site-assistant__status"
            aria-live="polite"
          >
            暂未找到匹配网站，试试补充你的具体目标或工具偏好。
          </p>

          <div
            v-else-if="status === 'unauthorized'"
            class="ai-site-assistant__feedback"
            role="alert"
          >
            <p>登录状态已失效，请重新登录后继续使用知航AI助手。</p>
            <button type="button" @click="goToLogin">重新登录</button>
          </div>

          <p
            v-else-if="status === 'error'"
            class="ai-site-assistant__feedback ai-site-assistant__feedback--error"
            role="alert"
          >
            {{ errorMessage }}
          </p>

          <section
            v-if="status === 'success'"
            class="ai-site-assistant__results"
            aria-label="知航AI推荐网站"
          >
            <p class="ai-site-assistant__results-title">
              为你找到 {{ results.length }} 个网站
            </p>
            <article
              v-for="site in results"
              :key="site.id || site.url || site.name"
              class="ai-site-assistant__result"
            >
              <FavoriteStarButton :site="site" size="sm" />
              <div class="ai-site-assistant__result-head">
                <img
                  v-if="getSiteLogo(site) && !hasLogoFailed(site)"
                  :src="getSiteLogo(site)"
                  :alt="`${site.name || '网站'} Logo`"
                  @error="markLogoFailed(site)"
                />
                <span
                  v-else
                  class="ai-site-assistant__text-logo"
                  aria-hidden="true"
                >
                  {{ getTextLogo(site) }}
                </span>
                <div>
                  <h3>{{ site.name || "推荐网站" }}</h3>
                  <span
                    v-if="site.category_name"
                    class="ai-site-assistant__category"
                  >
                    {{ site.category_name }}
                  </span>
                </div>
              </div>
              <p
                v-if="siteDescription(site)"
                class="ai-site-assistant__description"
              >
                {{ siteDescription(site) }}
              </p>
              <div v-if="site.reason" class="ai-site-assistant__reason">
                <strong>推荐原因</strong>
                <span>{{ site.reason }}</span>
              </div>
              <div v-if="site.match_status" class="ai-site-assistant__reason">
                <strong>{{ { full: '完全符合', partial: '部分符合', unverified: '信息待核实' }[site.match_status] }}</strong>
                <span v-for="item in site.unmet_conditions || []" :key="`unmet-${item}`">未满足：{{ item }}</span>
                <span v-for="item in site.unknown_conditions || []" :key="`unknown-${item}`">待核实：{{ item }}</span>
              </div>
              <button type="button" @click="emit('visit', site)">
                访问网站
              </button>
            </article>
          </section>
        </div>

        <form class="ai-site-assistant__composer" @submit.prevent="submitRecommendation">
          <label class="ai-site-assistant__sr-only" for="ai-site-assistant-query">
            描述你的需求
          </label>
          <textarea
            id="ai-site-assistant-query"
            ref="queryInput"
            v-model="query"
            maxlength="500"
            rows="3"
            placeholder="描述你的需求..."
            :disabled="isLoading"
            @keydown="handleKeydown"
            @compositionstart="isComposing = true"
            @compositionend="isComposing = false"
          />
          <div class="ai-site-assistant__composer-footer">
            <div class="ai-site-assistant__tools" aria-label="AI助手扩展功能">
              <button type="button" disabled aria-label="附件功能暂未接入">
                <Paperclip aria-hidden="true" />
              </button>
              <button type="button" disabled aria-label="联网功能暂未接入">
                <Globe2 aria-hidden="true" />
              </button>
              <button type="button" disabled aria-label="灵感功能暂未接入">
                <Lightbulb aria-hidden="true" />
              </button>
            </div>
            <span class="ai-site-assistant__count">{{ query.length }}/500</span>
            <button
              type="submit"
              class="ai-site-assistant__submit"
              :aria-label="isLoading ? '正在筛选' : '发送需求'"
              :disabled="!canSubmit"
            >
              <Send aria-hidden="true" />
            </button>
          </div>
          <p class="ai-site-assistant__disclaimer">
            AI生成内容仅供参考，请注意核实重要信息
          </p>
        </form>
      </aside>
      </div>
    </transition>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import {
  ArrowRight,
  Bot,
  ChevronLeft,
  FileText,
  Globe2,
  Lightbulb,
  MessageCircle,
  Minus,
  Paperclip,
  RefreshCw,
  Search,
  Send,
  Sparkles,
} from "lucide-vue-next";
import { useRouter } from "vue-router";
import FavoriteStarButton from "../site/FavoriteStarButton.vue";
import { useAiAssistantStore } from "../../stores/aiAssistant";
import { useUserStore } from "../../stores/user";
import { getAccessToken, isValidAuthToken } from "../../utils/auth";
import {
  aiAPI,
  getFaviconUrl,
  getSiteDescription,
  getTextLogo,
  unwrapResponse,
} from "../../utils/api";

const emit = defineEmits(["visit"]);
const router = useRouter();
const assistantStore = useAiAssistantStore();
const userStore = useUserStore();
const isOpen = computed(() => assistantStore.isOpen);
const loggedIn = computed(
  () => userStore.isLoggedIn && isValidAuthToken(getAccessToken()),
);
const query = ref("");
const queryInput = ref(null);
const isComposing = ref(false);
const isLoading = ref(false);
const status = ref("initial");
const errorMessage = ref("");
const results = ref([]);
const understanding = ref({ conditions: [], clarifications: [], notice: '', degraded: false });
const requestGeneration = ref(0);
const failedLogoKeys = ref(new Set());
const examples = [
  "检查 Python 报错",
  "找翻译英文资料的网站",
  "制作海报和图片素材",
];

const canSubmit = computed(
  () => query.value.trim().length >= 2 && !isLoading.value,
);

watch(isOpen, async (opened) => {
  if (!opened) return;
  await nextTick();
  queryInput.value?.focus();
});

// The assistant is global: invalidate account-scoped results on every route.
watch(() => [loggedIn.value, userStore.userInfo?.id || userStore.userInfo?.username], invalidateAssistantSession);

function invalidateAssistantSession() {
  requestGeneration.value += 1;
  closeAssistant();
  query.value = '';
  results.value = [];
  understanding.value = { conditions: [], clarifications: [], notice: '', degraded: false };
  errorMessage.value = '';
  status.value = 'initial';
  isLoading.value = false;
}

function closeAssistant() {
  assistantStore.closeAssistant();
}

function toggleAssistant() {
  assistantStore.toggleAssistant();
}

function handleLauncher() {
  if (loggedIn.value) {
    toggleAssistant();
    return;
  }
  goToLogin();
}

function fillExample(example) {
  query.value = example;
  queryInput.value?.focus();
}

function handleKeydown(event) {
  if (event.key === "Escape") {
    closeAssistant();
    return;
  }

  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.isComposing &&
    !isComposing.value
  ) {
    event.preventDefault();
    submitRecommendation();
  }
}

async function submitRecommendation() {
  if (!loggedIn.value) {
    goToLogin();
    return;
  }
  const trimmedQuery = query.value.trim();
  if (trimmedQuery.length < 2 || isLoading.value) return;
  const generation = ++requestGeneration.value;

  isLoading.value = true;
  status.value = "loading";
  errorMessage.value = "";
  results.value = [];
  understanding.value = { conditions: [], clarifications: [], notice: '', degraded: false };

  try {
    const response = await aiAPI.recommendSites({
      query: trimmedQuery,
      limit: 5,
    });
    if (generation !== requestGeneration.value || !loggedIn.value) return;
    const payload = unwrapResponse(response) || {};
    const items = Array.isArray(payload) ? payload : payload.items;
    results.value = Array.isArray(items) ? items : [];
    understanding.value = {
      conditions: payload.requirements?.conditions || [],
      clarifications: payload.clarifications || [],
      notice: payload.notice || '',
      degraded: Boolean(payload.degraded),
    };
    status.value = understanding.value.clarifications.length ? 'clarification' : results.value.length ? "success" : "empty";
  } catch (error) {
    if (generation !== requestGeneration.value || !loggedIn.value) return;
    const statusCode = error?.response?.status;
    if (statusCode === 401 || statusCode === 422) {
      status.value = "unauthorized";
    } else {
      status.value = "error";
      errorMessage.value =
        error?.response?.data?.msg ||
        error?.response?.data?.message ||
        "推荐暂时不可用，请稍后再试。";
    }
  } finally {
    if (generation === requestGeneration.value) isLoading.value = false;
  }
}

function getSiteKey(site) {
  return String(site?.id || site?.url || site?.name || "unknown");
}

function hasLogoFailed(site) {
  return failedLogoKeys.value.has(getSiteKey(site));
}

function markLogoFailed(site) {
  failedLogoKeys.value = new Set([...failedLogoKeys.value, getSiteKey(site)]);
}

function getSiteLogo(site) {
  return getFaviconUrl(site);
}

function siteDescription(site) {
  return getSiteDescription(site);
}

function goToLogin() {
  router.push({ path: "/login", query: { redirect: "/" } });
}

function handleDocumentKeydown(event) {
  if (event.key === "Escape" && isOpen.value) {
    closeAssistant();
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleDocumentKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleDocumentKeydown);
});
</script>

<style scoped>
.ai-site-assistant__launcher {
  position: fixed;
  top: 22%;
  right: 24px;
  z-index: 200;
  display: grid;
  width: 56px;
  height: 170px;
  place-items: center;
  border: 1px solid #e8edf3;
  border-radius: 28px;
  background: #ffffff;
  color: #0a234a;
  padding: 14px 0 12px;
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.04);
  font: inherit;
  font-family: "Songti SC", "STSong", "SimSun", serif;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.45;
  cursor: pointer;
  transition:
    transform var(--transition),
    box-shadow var(--transition);
}

.ai-site-assistant__launcher:hover,
.ai-site-assistant__launcher:focus-visible {
  transform: translateX(-2px);
  box-shadow: 0 8px 26px rgba(15, 23, 42, 0.06);
  outline: none;
}

.ai-site-assistant__launcher > svg:first-child {
  width: 28px;
  height: 28px;
  color: var(--primary);
}

.ai-site-assistant__launcher-arrow {
  width: 18px;
  height: 18px;
  color: #0a234a;
}

.ai-site-assistant__overlay {
  position: fixed;
  z-index: 300;
  top: 0;
  right: 0;
  bottom: 0;
  width: var(--ai-panel-width);
  display: flex;
  justify-content: flex-end;
  background: transparent;
}

.ai-site-assistant__panel {
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  overflow: hidden;
  border-left: 1px solid var(--color-border);
  background: #ffffff;
  box-shadow: -10px 0 30px rgba(15, 23, 42, 0.08);
}

.ai-drawer-enter-active,
.ai-drawer-leave-active {
  transition: opacity 300ms cubic-bezier(0.22, 1, 0.36, 1);
}

.ai-drawer-enter-active .ai-site-assistant__panel,
.ai-drawer-leave-active .ai-site-assistant__panel {
  transition: transform 300ms cubic-bezier(0.22, 1, 0.36, 1);
}

.ai-drawer-enter-from,
.ai-drawer-leave-to {
  opacity: 0;
}

.ai-drawer-enter-from .ai-site-assistant__panel,
.ai-drawer-leave-to .ai-site-assistant__panel {
  transform: translateX(100%);
}

.ai-site-assistant__header {
  position: relative;
  z-index: 1;
  top: 0;
  flex: 0 0 auto;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid var(--color-border-soft);
  background: #ffffff;
  padding: 22px 22px 18px;
  backdrop-filter: none;
}

.ai-site-assistant__eyebrow,
.ai-site-assistant__results-title {
  margin: 0;
  color: var(--color-primary-dark);
  font-size: 12px;
  font-weight: 800;
}

h2,
h3 {
  margin: 0;
  color: var(--color-heading);
}

h2 {
  margin-top: 4px;
  font-size: 22px;
}

h3 {
  font-size: 16px;
}

.ai-site-assistant__close {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  background: var(--primary-light);
  color: var(--color-heading);
  font-size: 25px;
  line-height: 1;
  cursor: pointer;
}

.ai-site-assistant__body {
  display: grid;
  min-height: 0;
  flex: 1 1 auto;
  gap: 20px;
  overflow-y: auto;
  padding: 22px;
}

form,
.ai-site-assistant__results {
  display: grid;
  gap: 10px;
}

label {
  color: var(--color-heading);
  font-size: 14px;
  font-weight: 800;
}

textarea {
  width: 100%;
  resize: vertical;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  color: var(--color-heading);
  background: #ffffff;
  padding: 12px;
  font: inherit;
  line-height: 1.55;
}

textarea:focus-visible,
button:focus-visible {
  border-color: var(--color-primary);
  outline: 3px solid color-mix(in srgb, var(--primary) 12%, transparent);
  outline-offset: 2px;
}

.ai-site-assistant__form-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.ai-site-assistant__submit,
.ai-site-assistant__result > button,
.ai-site-assistant__feedback button {
  min-height: 42px;
  border: 0;
  border-radius: 999px;
  background: var(--color-primary);
  color: #ffffff;
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.ai-site-assistant__submit:disabled,
.ai-site-assistant__examples button:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.ai-site-assistant__examples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.ai-site-assistant__examples button {
  border: 1px solid var(--color-border-soft);
  border-radius: 999px;
  background: var(--color-soft);
  color: var(--color-heading);
  padding: 6px 9px;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.ai-site-assistant__status,
.ai-site-assistant__feedback {
  margin: 0;
  border-radius: 12px;
  background: var(--color-soft);
  color: var(--color-text);
  padding: 12px;
  font-size: 14px;
  line-height: 1.55;
}

.ai-site-assistant__feedback {
  display: grid;
  gap: 10px;
  border: 1px solid var(--primary-border);
  background: var(--primary-light);
}

.ai-site-assistant__feedback p {
  margin: 0;
}

.ai-site-assistant__feedback--error {
  color: #b42318;
}

.ai-site-assistant__result {
  position: relative;
  display: grid;
  gap: 12px;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 14px;
}

.ai-site-assistant__result-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-site-assistant__result-head img,
.ai-site-assistant__text-logo {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  border: 1px solid var(--color-border-soft);
  border-radius: 12px;
  object-fit: cover;
}

.ai-site-assistant__text-logo {
  display: grid;
  place-items: center;
  background: var(--color-soft-orange);
  color: var(--color-primary-dark);
  font-weight: 900;
}

.ai-site-assistant__category {
  display: inline-block;
  margin-top: 4px;
  color: var(--color-primary-dark);
  font-size: 12px;
  font-weight: 750;
}

.ai-site-assistant__description,
.ai-site-assistant__reason {
  margin: 0;
  color: var(--color-text);
  font-size: 13px;
  line-height: 1.55;
}

.ai-site-assistant__reason {
  display: grid;
  gap: 3px;
  border-radius: 10px;
  background: var(--color-soft-orange);
  padding: 9px 10px;
}

.ai-site-assistant__reason strong {
  color: var(--color-primary-dark);
  font-size: 12px;
}

/* Reference-panel treatment: all rules remain local to the assistant. */
.ai-site-assistant__panel {
  color: #536987;
  border-left-color: rgba(55, 90, 145, 0.1);
  background: #ffffff;
  box-shadow: -10px 0 30px rgba(15, 23, 42, 0.08);
  font-family: "Songti SC", "STSong", "SimSun", "Noto Serif SC", serif;
}

.ai-site-assistant__panel button,
.ai-site-assistant__panel textarea {
  font-family: inherit;
}

.ai-site-assistant__header {
  min-height: 90px;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #e8edf3;
  background: #ffffff;
  padding: 20px 20px 12px;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.ai-site-assistant__header-copy,
.ai-site-assistant__header-actions {
  display: flex;
  align-items: center;
}

.ai-site-assistant__header-copy {
  min-width: 0;
  gap: 12px;
}

.ai-site-assistant__header-icon {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: var(--primary-soft);
  color: var(--primary);
}

.ai-site-assistant__header-icon svg {
  width: 21px;
  height: 21px;
}

.ai-site-assistant__header h2 {
  margin: 0;
  color: #14243d;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.2;
}

.ai-site-assistant__header .ai-site-assistant__eyebrow {
  margin-top: 5px;
  color: #7e91aa;
  font-size: 14px;
  font-weight: 500;
}

.ai-site-assistant__header-actions {
  flex: 0 0 auto;
  gap: 8px;
}

.ai-site-assistant__minimize,
.ai-site-assistant__close {
  display: grid;
  width: 42px;
  height: 42px;
  min-height: 42px;
  place-items: center;
  border: 1px solid #e3e8ef;
  border-radius: 50%;
  background: #ffffff;
  color: #294466;
  box-shadow: none;
  transition: background-color 180ms ease, color 180ms ease, transform 180ms ease;
}

.ai-site-assistant__minimize svg {
  width: 18px;
  height: 18px;
}

.ai-site-assistant__close {
  font-size: 24px;
}

.ai-site-assistant__minimize:hover,
.ai-site-assistant__close:hover {
  background: #f8fafc;
  color: var(--primary);
}

.ai-site-assistant__tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  flex: 0 0 auto;
  gap: 10px;
  padding: 10px 20px 16px;
}

.ai-site-assistant__tabs button {
  display: inline-flex;
  min-width: 0;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid #e3e8ef;
  border-radius: 999px;
  background: #ffffff;
  color: #223958;
  font-size: 14px;
  font-weight: 600;
  opacity: 1;
}

.ai-site-assistant__tabs button:disabled {
  color: #223958;
  cursor: default;
  opacity: 1;
}

.ai-site-assistant__tabs button svg {
  width: 17px;
  height: 17px;
}

.ai-site-assistant__tabs button.is-active {
  border-color: var(--primary);
  background: var(--primary);
  color: #fff;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--primary) 12%, transparent);
}

.ai-site-assistant__body {
  display: grid;
  align-content: start;
  gap: 18px;
  padding: 8px 20px 14px;
  scrollbar-width: thin;
  scrollbar-color: rgba(70, 100, 145, 0.16) transparent;
}

.ai-site-assistant__body::-webkit-scrollbar {
  width: 5px;
}

.ai-site-assistant__body::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(70, 100, 145, 0.16);
}

.ai-site-assistant__welcome {
  margin: 0;
  border: 1px solid #e8edf3;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.04);
  padding: 20px;
}

.ai-site-assistant__welcome h3 {
  margin: 0;
  color: #14243d;
  font-size: 18px;
  font-weight: 600;
}

.ai-site-assistant__welcome p {
  margin: 10px 0 0;
  color: #5f718d;
  font-size: 14px;
  line-height: 1.8;
}

.ai-site-assistant__examples {
  display: grid;
  gap: 10px;
  border: 0;
  border-radius: 20px;
  background: #ffffff;
  color: #536987;
  padding: 18px;
}

.ai-site-assistant__examples-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ai-site-assistant__examples-heading strong {
  color: #14243d;
  font-size: 15px;
  font-weight: 600;
}

.ai-site-assistant__refresh {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #627798;
  font-size: 14px;
}

.ai-site-assistant__refresh svg {
  width: 15px;
  height: 15px;
}

.ai-site-assistant__examples button {
  display: flex;
  width: 100%;
  min-height: 50px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #e8edf3;
  border-radius: 16px;
  background: #ffffff;
  color: #536987;
  box-shadow: 0 3px 10px rgba(40, 65, 105, 0.025);
  padding: 0 16px;
  font-size: 14px;
  line-height: 1.45;
  text-align: left;
  transition: background-color 180ms ease, color 180ms ease, transform 180ms ease;
}

.ai-site-assistant__examples button svg {
  width: 17px;
  height: 17px;
  flex: 0 0 auto;
  color: var(--primary);
}

.ai-site-assistant__examples button:hover:not(:disabled) {
  background: #f8fafc;
  transform: translateX(2px);
}

.ai-site-assistant__composer {
  display: grid;
  flex: 0 0 auto;
  gap: 8px;
  margin: 14px 20px 10px;
  border: 1px solid #e3e8ef;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.04);
  padding: 14px 14px 10px;
}

.ai-site-assistant__composer textarea {
  width: 100%;
  min-height: 55px;
  max-height: 140px;
  resize: none;
  border: 0;
  border-radius: 0;
  outline: none;
  color: #263d5e;
  background: transparent;
  padding: 0;
  font-size: 15px;
  line-height: 1.6;
  box-shadow: none;
}

.ai-site-assistant__composer textarea::placeholder {
  color: #93a1b5;
}

.ai-site-assistant__composer-footer {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-site-assistant__tools {
  display: flex;
  gap: 6px;
}

.ai-site-assistant__tools button {
  display: grid;
  width: 32px;
  min-width: 32px;
  height: 32px;
  min-height: 32px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: #172f50;
  opacity: 0.48;
}

.ai-site-assistant__tools button svg {
  width: 17px;
  height: 17px;
}

.ai-site-assistant__count {
  margin-left: auto;
  color: #8d9aaf;
  font-size: 12px;
}

.ai-site-assistant__submit {
  display: grid;
  width: 46px;
  min-width: 46px;
  height: 46px;
  min-height: 46px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--primary) 12%, transparent);
  padding: 0;
  transition: background-color 180ms ease, transform 180ms ease;
}

.ai-site-assistant__submit svg {
  width: 19px;
  height: 19px;
}

.ai-site-assistant__submit:hover:not(:disabled) {
  background: var(--primary-hover);
  transform: translateY(-1px);
}

.ai-site-assistant__submit:active:not(:disabled) {
  transform: scale(0.97);
}

.ai-site-assistant__disclaimer {
  margin: 0;
  color: #8a99af;
  font-size: 12px;
  text-align: center;
}

.ai-site-assistant__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
}

@media (max-width: 1100px) {
  .ai-site-assistant__overlay {
    width: 100%;
    padding: 0;
    background: #ffffff;
  }

  .ai-site-assistant__panel {
    width: min(420px, 92vw);
  }
}

@media (max-width: 600px) {
  .ai-site-assistant__launcher {
    right: 16px;
    top: auto;
    bottom: 80px;
    width: auto;
    height: 48px;
    grid-auto-flow: column;
    gap: 8px;
    border-radius: 24px;
    padding: 0 14px;
  }

  .ai-site-assistant__overlay {
    padding: 12px;
    align-items: flex-end;
  }

  .ai-site-assistant__panel {
    width: 100%;
    height: min(82vh, 720px);
    border: 1px solid var(--color-border);
    border-radius: 20px;
  }
}
</style>
