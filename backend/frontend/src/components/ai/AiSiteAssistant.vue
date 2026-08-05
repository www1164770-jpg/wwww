<template>
  <div class="ai-site-assistant">
    <button
      type="button"
      class="ai-site-assistant__launcher"
      aria-label="打开知航AI助手"
      :aria-expanded="isOpen"
      aria-controls="ai-site-assistant-panel"
      @click="toggleAssistant"
    >
      <span aria-hidden="true">✦</span>
      知航AI帮我找网站
    </button>

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
          <div>
            <p class="ai-site-assistant__eyebrow">知航AI助手</p>
            <h2 id="ai-site-assistant-title">描述你的需求</h2>
          </div>
          <button
            type="button"
            class="ai-site-assistant__close"
            aria-label="关闭知航AI助手"
            @click="closeAssistant"
          >
            ×
          </button>
        </header>

        <div class="ai-site-assistant__body">
          <form @submit.prevent="submitRecommendation">
            <label for="ai-site-assistant-query">你想完成什么？</label>
            <textarea
              id="ai-site-assistant-query"
              ref="queryInput"
              v-model="query"
              maxlength="500"
              rows="4"
              placeholder="例如：我需要检查 Python 报错并查找可靠的资料"
              :disabled="isLoading"
              @keydown="handleKeydown"
              @compositionstart="isComposing = true"
              @compositionend="isComposing = false"
            />
            <div class="ai-site-assistant__form-meta">
              <span>Enter 提交，Shift + Enter 换行</span>
              <span>{{ query.length }}/500</span>
            </div>
            <button
              type="submit"
              class="ai-site-assistant__submit"
              :disabled="!canSubmit"
            >
              {{ isLoading ? "正在筛选…" : "帮我找网站" }}
            </button>
          </form>

          <div class="ai-site-assistant__examples" aria-label="示例需求">
            <span>试试这样说：</span>
            <button
              v-for="example in examples"
              :key="example"
              type="button"
              :disabled="isLoading"
              @click="fillExample(example)"
            >
              {{ example }}
            </button>
          </div>

          <p
            v-if="status === 'loading'"
            class="ai-site-assistant__status"
            aria-live="polite"
          >
            正在从平台网站中为你筛选……
          </p>

          <p
            v-else-if="status === 'empty'"
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
              <button type="button" @click="emit('visit', site)">
                访问网站
              </button>
            </article>
          </section>
        </div>
      </aside>
    </div>
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
import { useRouter } from "vue-router";
import FavoriteStarButton from "../site/FavoriteStarButton.vue";
import { useAiAssistantStore } from "../../stores/aiAssistant";
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
const isOpen = computed(() => assistantStore.isOpen);
const query = ref("");
const queryInput = ref(null);
const isComposing = ref(false);
const isLoading = ref(false);
const status = ref("initial");
const errorMessage = ref("");
const results = ref([]);
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

function openAssistant() {
  assistantStore.openAssistant();
}

function closeAssistant() {
  assistantStore.closeAssistant();
}

function toggleAssistant() {
  assistantStore.toggleAssistant();
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
  const trimmedQuery = query.value.trim();
  if (trimmedQuery.length < 2 || isLoading.value) return;

  isLoading.value = true;
  status.value = "loading";
  errorMessage.value = "";

  try {
    const response = await aiAPI.recommendSites({
      query: trimmedQuery,
      limit: 5,
    });
    const payload = unwrapResponse(response) || {};
    const items = Array.isArray(payload) ? payload : payload.items;
    results.value = Array.isArray(items) ? items : [];
    status.value = results.value.length ? "success" : "empty";
  } catch (error) {
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
    isLoading.value = false;
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
  right: 24px;
  bottom: 92px;
  z-index: 16;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 46px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(135deg, #ff7058, #f0446b);
  color: #ffffff;
  padding: 0 18px;
  box-shadow: 0 14px 30px rgba(240, 68, 107, 0.28);
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform var(--transition),
    box-shadow var(--transition);
}

.ai-site-assistant__launcher:hover,
.ai-site-assistant__launcher:focus-visible {
  transform: translateY(-2px);
  box-shadow: 0 18px 34px rgba(240, 68, 107, 0.36);
  outline: none;
}

.ai-site-assistant__overlay {
  position: fixed;
  z-index: 17;
  inset: 0;
  display: flex;
  justify-content: flex-end;
  background: rgba(15, 23, 42, 0.18);
}

.ai-site-assistant__panel {
  width: min(400px, calc(100vw - 32px));
  height: 100%;
  overflow-y: auto;
  border-left: 1px solid var(--color-border);
  background: #ffffff;
  box-shadow: -18px 0 44px rgba(15, 23, 42, 0.14);
}

.ai-site-assistant__header {
  position: sticky;
  z-index: 1;
  top: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  border-bottom: 1px solid var(--color-border-soft);
  background: rgba(255, 255, 255, 0.96);
  padding: 22px 22px 18px;
  backdrop-filter: blur(12px);
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
  background: #ffffff;
  color: var(--color-heading);
  font-size: 25px;
  line-height: 1;
  cursor: pointer;
}

.ai-site-assistant__body {
  display: grid;
  gap: 20px;
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
  outline: 3px solid rgba(255, 112, 88, 0.2);
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
  border: 1px solid rgba(255, 112, 88, 0.22);
  background: var(--color-soft-orange);
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

@media (max-width: 600px) {
  .ai-site-assistant__launcher {
    right: 16px;
    bottom: 80px;
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
