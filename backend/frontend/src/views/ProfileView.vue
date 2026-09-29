<template>
  <div class="page profile-page">
    <main class="profile-shell">
      <aside class="profile-sidebar" aria-label="个人中心菜单">
        <div class="profile-sidebar__identity">
          <div class="profile-avatar" aria-hidden="true">
            {{ String(profile.user?.username || "用户").slice(0, 1) }}
          </div>
          <div class="profile-sidebar__identity-copy">
            <strong>{{ profile.user?.username || "用户" }}</strong>
            <span>{{ profile.user?.email || "暂无邮箱" }}</span>
            <small>{{ roleText(profile.user?.role) }}</small>
          </div>
        </div>

        <nav class="profile-sidebar__nav" aria-label="个人中心菜单">
          <RouterLink
            class="profile-nav-item"
            :class="{ 'profile-nav-item--active': activeSection === 'profile' }"
            :to="{ name: 'Profile' }"
          >
            <UserRound aria-hidden="true" />
            <span>个人中心</span>
          </RouterLink>
          <RouterLink
            class="profile-nav-item"
            :class="{ 'profile-nav-item--active': activeSection === 'personalization' }"
            :to="profileSectionLink('personalization')"
          >
            <Settings2 aria-hidden="true" />
            <span>个性化设置</span>
          </RouterLink>
          <RouterLink
            class="profile-nav-item"
            :class="{ 'profile-nav-item--active': activeSection === 'survey' }"
            :to="profileSectionLink('survey')"
          >
            <ClipboardList aria-hidden="true" />
            <span>我的问卷</span>
          </RouterLink>
          <RouterLink
            class="profile-nav-item"
            :class="{ 'profile-nav-item--active': activeSection === 'favorites' }"
            :to="profileSectionLink('favorites')"
          >
            <Star aria-hidden="true" />
            <span>我的收藏</span>
          </RouterLink>
          <RouterLink
            class="profile-nav-item"
            :class="{ 'profile-nav-item--active': activeSection === 'history' }"
            :to="profileSectionLink('history')"
          >
            <History aria-hidden="true" />
            <span>浏览历史</span>
          </RouterLink>
          <RouterLink
            class="profile-nav-item"
            :class="{ 'profile-nav-item--active': activeSection === 'password' }"
            :to="profileSectionLink('password')"
          >
            <KeyRound aria-hidden="true" />
            <span>修改密码</span>
          </RouterLink>
        </nav>
      </aside>

      <section class="profile-content" :data-active-section="activeSection">
        <LoadingState v-if="loading" text="正在加载个人中心..." />
        <EmptyState
          v-else-if="error"
          title="个人中心加载失败"
          :description="error"
        />
        <template v-else>
          <header v-show="activeSection === 'profile'" class="profile-hero profile-section-panel">
            <div class="profile-hero__copy">
              <div class="profile-avatar profile-avatar--hero" aria-hidden="true">
                {{ String(profile.user?.username || "用户").slice(0, 1) }}
              </div>
              <div>
                <p class="profile-hero__eyebrow">个人工作台</p>
                <AnimatedPageTitle class="profile-hero__title" :animation="false"
                  >你好，{{ profile.user?.username || "用户" }}</AnimatedPageTitle
                >
                <div class="profile-hero__meta">
                  <span>{{ profile.user?.email || "暂无邮箱" }}</span>
                  <b>{{ roleText(profile.user?.role) }}</b>
                </div>
              </div>
            </div>
            <p class="profile-hero__motto">以知识为舟，驶向更广阔的可能。</p>
            <svg
              class="profile-hero__scenery"
              viewBox="0 0 360 170"
              fill="none"
              aria-hidden="true"
            >
              <path d="M4 146C50 127 78 80 121 111C161 139 198 68 239 106C278 142 308 120 356 73" />
              <path d="M52 151C96 133 138 154 180 132C224 109 271 147 344 119" />
              <path d="M274 42V115M274 42L292 59M274 42L258 59" />
              <circle cx="274" cy="34" r="5" />
            </svg>
          </header>

          <PersonalizationView
            v-show="activeSection === 'personalization'"
            class="profile-section-panel"
            embedded
          />

          <section v-show="activeSection === 'survey'" id="questionnaire" class="profile-card profile-survey-card profile-section-panel">
            <header class="profile-card__header">
              <div class="profile-card__title">
                <span class="profile-card__icon"><ClipboardList aria-hidden="true" /></span>
                <div>
                  <h2>我的问卷</h2>
                  <p>职业画像会帮助你发现更契合的资源方向。</p>
                </div>
              </div>
              <RouterLink class="profile-card__action" to="/questionnaire">
                更新问卷
                <ArrowUpRight aria-hidden="true" />
              </RouterLink>
            </header>
            <div v-if="hasQuestionnaire" class="survey-grid">
              <article class="survey-field">
                <span>职业</span>
                <strong>{{ labelText(profile.profile?.occupation) }}</strong>
              </article>
              <article class="survey-field">
                <span>能力水平</span>
                <strong>{{ labelText(profile.profile?.skill_level) }}</strong>
              </article>
              <article class="survey-field survey-field--wide">
                <span>兴趣</span>
                <div v-if="parseList(profile.profile?.interests).length" class="survey-tags">
                  <b v-for="item in parseList(profile.profile?.interests)" :key="`interest-${item}`">{{ labelText(item) }}</b>
                </div>
                <em v-else>暂无</em>
              </article>
              <article class="survey-field">
                <span>偏好</span>
                <div v-if="parseList(profile.profile?.preferences).length" class="survey-tags">
                  <b v-for="item in parseList(profile.profile?.preferences)" :key="`preference-${item}`">{{ labelText(item) }}</b>
                </div>
                <em v-else>暂无</em>
              </article>
              <article class="survey-field">
                <span>用途</span>
                <div v-if="parseList(profile.profile?.purposes).length" class="survey-tags">
                  <b v-for="item in parseList(profile.profile?.purposes)" :key="`purpose-${item}`">{{ labelText(item) }}</b>
                </div>
                <em v-else>暂无</em>
              </article>
            </div>
            <EmptyState
              v-else
              title="暂无问卷信息"
              description="完成职业问卷后，系统会为你推荐更适合的资源。"
              action-text="填写问卷"
              action-to="/questionnaire"
            />
          </section>

          <section v-show="activeSection === 'favorites'" id="favorites" class="profile-card profile-favorites-card profile-section-panel">
            <header class="profile-card__header">
              <div class="profile-card__title">
                <span class="profile-card__icon"><Star aria-hidden="true" /></span>
                <div>
                  <h2>我的收藏</h2>
                  <p>你保存的网站资源，都可以在这里继续查找。</p>
                </div>
              </div>
            </header>
            <div class="profile-favorites-card__entry">
              <span class="profile-favorites-card__star" aria-hidden="true"><Star /></span>
              <div>
                <strong>收藏入口</strong>
                <p>进入收藏页查看和管理你保存的网站资源。</p>
              </div>
              <RouterLink class="profile-primary-link" to="/favorites">
                查看收藏
                <ArrowUpRight aria-hidden="true" />
              </RouterLink>
            </div>
          </section>

          <section v-show="activeSection === 'history'" id="history" class="profile-card profile-history-card profile-section-panel">
            <div class="history-heading">
              <div class="profile-card__title">
                <span class="profile-card__icon"><History aria-hidden="true" /></span>
                <div>
                  <h2>浏览历史</h2>
                  <p>快速回到你近期浏览过的网站资源。</p>
                </div>
              </div>
              <button
                v-if="historyItems.length"
                type="button"
                class="history-clear"
                :disabled="historyMutating"
                @click="clearHistory"
              >
                <Trash2 aria-hidden="true" />
                清空历史
              </button>
            </div>
            <LoadingState v-if="historyLoading" text="正在加载浏览历史..." />
            <div v-else-if="historyError" class="history-error" role="alert">
              <span>{{ historyError }}</span>
              <button type="button" @click="loadHistory">
                <RotateCw aria-hidden="true" />
                重新加载
              </button>
            </div>
            <EmptyState
              v-if="!historyLoading && !historyItems.length"
              title="暂无浏览历史"
              description="访问过的网站后续会在这里展示。"
            />
            <div v-else-if="!historyLoading" class="history-list">
              <article
                v-for="item in historyItems"
                :key="item.local_id || item.server_id || item.id"
                class="history-item"
              >
                <button
                  type="button"
                  class="history-visit"
                  :aria-label="`再次访问 ${item.name}`"
                  @click="visitHistoryItem(item)"
                >
                  <SiteLogo
                    :name="item.name"
                    :url="item.url"
                    :logo="item.logo_url"
                    size="md"
                    decorative
                  />
                  <span class="history-copy">
                    <span class="history-title-row">
                      <strong>{{ item.name }}</strong>
                      <ExternalLink aria-hidden="true" />
                    </span>
                    <span v-if="item.description" class="history-description">
                      {{ item.description }}
                    </span>
                    <span class="history-meta">
                      <b v-if="item.category">{{ item.category }}</b>
                      <time :datetime="item.visited_at">
                        {{ formatVisitedAt(item.visited_at) }}
                      </time>
                    </span>
                  </span>
                </button>
                <button
                  type="button"
                  class="history-delete"
                  :disabled="historyMutating"
                  :aria-label="`删除 ${item.name} 的浏览记录`"
                  title="删除记录"
                  @click="removeHistoryItem(item)"
                >
                  <Trash2 aria-hidden="true" />
                </button>
              </article>
            </div>
          </section>

          <section v-show="activeSection === 'password'" id="password" class="profile-card profile-password-card profile-section-panel">
            <header class="profile-card__header">
              <div class="profile-card__title">
                <span class="profile-card__icon"><KeyRound aria-hidden="true" /></span>
                <div>
                  <h2>修改密码</h2>
                  <p>定期更新密码，保障你的账号安全。</p>
                </div>
              </div>
            </header>
            <div class="profile-password-card__row">
              <label>
                旧密码
                <input
                  v-model="oldPassword"
                  type="password"
                  autocomplete="current-password"
                />
              </label>
              <label>
                新密码
                <input
                  v-model="newPassword"
                  type="password"
                  autocomplete="new-password"
                />
              </label>
              <button
                type="button"
                :disabled="passwordLoading"
                @click="changePassword"
              >
                {{ passwordLoading ? "处理中..." : "更新" }}
              </button>
            </div>
          </section>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import {
  ArrowUpRight,
  ClipboardList,
  ExternalLink,
  History,
  KeyRound,
  RotateCw,
  Settings2,
  Star,
  Trash2,
  UserRound,
} from "lucide-vue-next";
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import AnimatedPageTitle from "../components/common/AnimatedPageTitle.vue";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SiteLogo from "../components/site/SiteLogo.vue";
import PersonalizationView from "./PersonalizationView.vue";
import { userAPI } from "../utils/api";
import {
  clearBrowsingHistory,
  deleteBrowsingHistory,
  loadBrowsingHistory,
  visitSite,
} from "../utils/siteVisit";
import { errorToast, successToast } from "../utils/toast";

const profile = ref({});
const oldPassword = ref("");
const newPassword = ref("");
const loading = ref(false);
const error = ref("");
const passwordLoading = ref(false);
const historyItems = ref([]);
const historyLoading = ref(false);
const historyError = ref("");
const historyMutating = ref(false);
const hasQuestionnaire = computed(() => Boolean(profile.value.profile));
const route = useRoute();
const profileSections = new Set(["personalization", "survey", "favorites", "history", "password"]);
const activeSection = computed(() => {
  const section = String(route.params.section || "profile");
  return profileSections.has(section) ? section : "profile";
});

function profileSectionLink(section) {
  return { name: "ProfileSection", params: { section } };
}

const labelMap = {
  programmer: "程序员",
  designer: "设计师",
  product_manager: "产品经理",
  operations: "运营",
  marketing: "市场营销",
  ecommerce: "电商从业者",
  teacher: "教师",
  student: "学生",
  creator: "内容创作者",
  other: "其他",
  beginner: "入门",
  junior: "初级",
  intermediate: "中级",
  senior: "高级",
};

function parseList(value) {
  if (Array.isArray(value)) return value;
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return String(value)
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
}

function labelText(value) {
  return labelMap[value] || value || "未填写";
}

function listText(value) {
  const items = parseList(value).map((item) => labelMap[item] || item);
  return items.length ? items.join("、") : "暂无";
}

function roleText(value) {
  return { admin: "管理员", super_admin: "超级管理员", user: "普通用户" }[
    value || "user"
  ];
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const response = await userAPI.getProfile();
    profile.value = response.data?.data || {};
  } catch (err) {
    error.value = err.response?.data?.msg || "个人中心加载失败，请稍后重试";
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}
async function loadHistory() {
  historyLoading.value = true;
  historyError.value = "";
  try {
    const result = await loadBrowsingHistory();
    historyItems.value = result.items;
    if (result.syncError) {
      historyError.value = "服务器历史暂时无法同步，当前展示本地记录。";
    }
  } catch (err) {
    historyItems.value = [];
    historyError.value =
      err?.response?.data?.msg || "浏览历史加载失败，请稍后重试。";
  } finally {
    historyLoading.value = false;
  }
}

function visitHistoryItem(item) {
  visitSite(item, { source: "site_detail" });
  void loadHistory();
}

async function removeHistoryItem(item) {
  if (!window.confirm(`确定删除“${item.name}”的浏览记录吗？`)) return;
  historyMutating.value = true;
  try {
    await deleteBrowsingHistory(item);
    historyItems.value = historyItems.value.filter(
      (entry) =>
        (entry.local_id || entry.server_id || entry.id) !==
        (item.local_id || item.server_id || item.id),
    );
    successToast("浏览记录已删除");
  } catch (err) {
    errorToast(err?.response?.data?.msg || "删除失败，请稍后重试");
    await loadHistory();
  } finally {
    historyMutating.value = false;
  }
}

async function clearHistory() {
  if (!window.confirm("确定清空全部浏览历史吗？此操作无法撤销。")) return;
  historyMutating.value = true;
  try {
    await clearBrowsingHistory();
    historyItems.value = [];
    successToast("浏览历史已清空");
  } catch (err) {
    errorToast(err?.response?.data?.msg || "清空失败，请稍后重试");
    await loadHistory();
  } finally {
    historyMutating.value = false;
  }
}

function formatVisitedAt(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
async function changePassword() {
  if (passwordLoading.value) return;
  if (!oldPassword.value || !newPassword.value) {
    errorToast("请输入密码");
    return;
  }
  passwordLoading.value = true;
  try {
    await userAPI.changePassword(oldPassword.value, newPassword.value);
    oldPassword.value = "";
    newPassword.value = "";
    successToast("保存成功");
  } catch (err) {
    errorToast(err.response?.data?.msg || "操作失败，请稍后重试");
  } finally {
    passwordLoading.value = false;
  }
}
onMounted(() => {
  void load();
  void loadHistory();
});
</script>

<style scoped>
.profile-page {
  --profile-primary: var(--primary);
  --profile-primary-light: var(--primary-soft);
  --profile-text: var(--app-text-primary);
  --profile-muted: var(--app-text-muted);
  --profile-border: var(--surface-border);
  --profile-surface: var(--surface);

  min-height: 100vh;
  background: var(--page-bg);
  padding: 0 0 84px;
}

.profile-shell {
  display: grid;
  width: min(1440px, calc(100% - 48px));
  grid-template-columns: 232px minmax(0, 1fr);
  align-items: start;
  gap: 24px;
  margin: 0 auto;
}

.profile-sidebar {
  position: sticky;
  top: 92px;
  display: grid;
  gap: 16px;
  border: 1px solid var(--profile-border);
  border-radius: 18px;
  background: var(--profile-surface);
  padding: 18px 12px 12px;
  box-shadow: var(--app-card-shadow);
}

.profile-sidebar__identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
  padding: 5px 8px 17px;
  border-bottom: 1px solid var(--profile-border);
}

.profile-avatar {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--primary-border);
  border-radius: 50%;
  background: var(--profile-primary-light);
  color: var(--profile-primary);
  font-size: 18px;
  font-weight: 700;
}

.profile-sidebar__identity-copy {
  display: grid;
  min-width: 0;
  gap: 3px;
}

.profile-sidebar__identity-copy strong {
  overflow: hidden;
  color: var(--profile-text);
  font-size: 15px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-sidebar__identity-copy span {
  overflow: hidden;
  color: var(--profile-muted);
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-sidebar__identity-copy small {
  color: var(--text-tertiary);
  font-size: 12px;
}

.profile-sidebar__nav {
  display: grid;
  gap: 4px;
}

.profile-nav-item {
  position: relative;
  display: flex;
  min-height: 48px;
  align-items: center;
  gap: 11px;
  border-radius: 10px;
  color: var(--text-secondary);
  padding: 0 12px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.profile-nav-item svg {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
}

.profile-nav-item:hover,
.profile-nav-item:focus-visible {
  background: var(--surface-hover);
  color: var(--profile-primary);
  outline: none;
}

.profile-nav-item--active,
.profile-nav-item.router-link-active {
  background: var(--profile-primary-light);
  color: var(--profile-primary);
}

.profile-nav-item--active::before,
.profile-nav-item.router-link-active::before {
  position: absolute;
  left: -12px;
  width: 3px;
  height: 24px;
  border-radius: 0 4px 4px 0;
  background: var(--profile-primary);
  content: "";
}

.profile-content {
  display: grid;
  min-width: 0;
  gap: 20px;
  scroll-margin-top: 96px;
}

.profile-section-panel {
  animation: profile-section-enter 200ms ease-out both;
}

@keyframes profile-section-enter {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.profile-content > :deep(.loading-state),
.profile-content > :deep(.empty-state) {
  border-color: var(--profile-border);
  border-radius: 18px;
  background: var(--profile-surface);
  box-shadow: var(--app-card-shadow);
}

.profile-hero {
  position: relative;
  display: grid;
  min-height: 168px;
  align-content: center;
  overflow: hidden;
  border: 1px solid var(--profile-border);
  border-radius: 18px;
  background: var(--profile-surface);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
  padding: 28px 34px;
}

.profile-hero__copy {
  position: relative;
  z-index: 1;
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 15px;
}

.profile-avatar--hero {
  width: 58px;
  height: 58px;
  border-color: var(--primary-border);
  background: var(--surface);
  box-shadow: 0 4px 12px color-mix(in srgb, var(--profile-primary) 8%, transparent);
  font-size: 24px;
}

.profile-hero__eyebrow {
  margin: 0 0 3px;
  color: var(--profile-primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.profile-hero__title {
  margin: 0;
  color: var(--profile-text);
  font-size: clamp(25px, 3vw, 34px);
  font-weight: 650;
  line-height: 1.25;
}

.profile-hero__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 7px;
  color: var(--profile-muted);
  font-size: 13px;
}

.profile-hero__meta b {
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary-text);
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 600;
}

.profile-hero__motto {
  position: relative;
  z-index: 1;
  margin: 12px 0 0 73px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

.profile-hero__scenery {
  position: absolute;
  right: -18px;
  bottom: -23px;
  width: min(48%, 440px);
  color: #8eaff2;
  opacity: 0.28;
}

.profile-hero__scenery path,
.profile-hero__scenery circle {
  stroke: currentColor;
  stroke-width: 2;
}

.profile-hero__scenery circle {
  fill: #ffffff;
}

.profile-card {
  display: grid;
  min-width: 0;
  gap: 20px;
  scroll-margin-top: 96px;
  border: 1px solid var(--profile-border);
  border-radius: 18px;
  background: var(--profile-surface);
  padding: 25px;
  box-shadow: var(--app-card-shadow);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
}

.profile-card__header,
.history-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.profile-card__title {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 11px;
}

.profile-card__icon {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 11px;
  background: var(--profile-primary-light);
  color: var(--profile-primary);
}

.profile-card__icon svg {
  width: 19px;
  height: 19px;
}

.profile-card__title h2 {
  margin: 0;
  color: var(--profile-text);
  font-size: 20px;
  font-weight: 650;
  line-height: 1.35;
}

.profile-card__title p {
  margin: 3px 0 0;
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.55;
}

.profile-card__action,
.profile-primary-link {
  display: inline-flex;
  min-height: 38px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border-radius: 10px;
  color: var(--profile-primary);
  padding: 0 10px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 650;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.profile-card__action svg,
.profile-primary-link svg {
  width: 16px;
  height: 16px;
}

.profile-card__action:hover,
.profile-card__action:focus-visible {
  background: var(--profile-primary-light);
  outline: none;
}

.survey-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.survey-field {
  display: grid;
  min-width: 0;
  align-content: start;
  gap: 8px;
  border: 1px solid var(--surface-border);
  border-radius: 12px;
  background: var(--surface-soft);
  padding: 14px;
}

.survey-field--wide {
  grid-column: 1 / -1;
}

.survey-field > span {
  color: var(--profile-muted);
  font-size: 12px;
  font-weight: 600;
}

.survey-field > strong {
  color: var(--profile-text);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.55;
}

.survey-field > em {
  color: var(--profile-muted);
  font-size: 14px;
  font-style: normal;
}

.survey-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.survey-tags b {
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--text-secondary);
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
}

.profile-survey-card :deep(.empty-state) {
  border-color: #e8edf5;
  border-radius: 12px;
  background: var(--surface-soft);
  padding: 28px 20px;
}

.profile-survey-card :deep(.empty-icon) {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--profile-primary-light);
  color: var(--profile-primary);
}

.profile-survey-card :deep(.empty-action) {
  min-height: 38px;
  border-radius: 10px;
  background: var(--profile-primary);
  box-shadow: none;
}

.profile-favorites-card {
  gap: 17px;
}

.profile-favorites-card__entry {
  display: grid;
  min-height: 118px;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  border: 1px solid var(--surface-border);
  border-radius: 14px;
  background: var(--surface-soft);
  padding: 17px 18px;
}

.profile-favorites-card__star {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  border-radius: 14px;
  background: var(--profile-primary-light);
  color: var(--profile-primary);
}

.profile-favorites-card__star svg {
  width: 24px;
  height: 24px;
  fill: currentColor;
}

.profile-favorites-card__entry strong {
  color: var(--profile-text);
  font-size: 15px;
  font-weight: 650;
}

.profile-favorites-card__entry p {
  margin: 5px 0 0;
  color: var(--profile-muted);
  font-size: 13px;
  line-height: 1.6;
}

.profile-primary-link {
  min-height: 40px;
  border: 1px solid var(--profile-primary);
  background: var(--profile-primary);
  color: #ffffff;
  padding: 0 13px;
}

.profile-primary-link:hover,
.profile-primary-link:focus-visible {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
  color: #ffffff;
  outline: none;
}

.history-clear,
.history-error button {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px solid var(--profile-border);
  border-radius: 10px;
  background: var(--surface);
  color: var(--text-secondary);
  padding: 0 12px;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.history-clear:hover,
.history-clear:focus-visible,
.history-error button:hover,
.history-error button:focus-visible {
  border-color: var(--primary-border);
  background: var(--profile-primary-light);
  color: var(--profile-primary);
  outline: none;
}

.history-clear:disabled {
  cursor: wait;
  opacity: 0.68;
}

.history-clear svg,
.history-error svg,
.history-delete svg {
  width: 17px;
  height: 17px;
}

.history-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-left: 3px solid #e3ae48;
  border-radius: 10px;
  background: #fffdf7;
  color: #715f3c;
  padding: 12px 14px;
  font-size: 13px;
}

.history-list {
  display: grid;
  gap: 10px;
}

.history-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 38px;
  align-items: center;
  gap: 10px;
  border: 1px solid #edf1f6;
  border-radius: 12px;
  background: var(--surface-soft);
  padding: 11px;
}

.history-visit {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 13px;
  border: 0;
  background: transparent;
  color: inherit;
  padding: 0;
  text-align: left;
  box-shadow: none;
}

.history-copy {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 5px;
}

.history-title-row,
.history-meta {
  display: flex;
  align-items: center;
}

.history-title-row {
  min-width: 0;
  gap: 7px;
}

.history-title-row strong {
  overflow: hidden;
  color: var(--profile-text);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-title-row svg {
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
  color: var(--profile-primary);
}

.history-description {
  overflow: hidden;
  color: var(--profile-muted);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-meta {
  flex-wrap: wrap;
  gap: 8px;
  color: var(--text-tertiary);
  font-size: 12px;
}

.history-meta b {
  color: var(--primary-text);
}

.history-delete {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #9aa5b6;
  padding: 0;
  box-shadow: none;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.history-delete:hover,
.history-delete:focus-visible {
  background: #fff2f2;
  color: #d55a5a;
  outline: none;
}

.profile-password-card__row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) auto;
  align-items: end;
  gap: 12px;
}

.profile-password-card__row label {
  display: grid;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.profile-password-card__row input {
  min-width: 0;
  border: 1px solid var(--profile-border);
  border-radius: 10px;
  background: var(--surface-soft);
  color: var(--profile-text);
  padding: 11px 12px;
  font: inherit;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.profile-password-card__row input:focus {
  border-color: var(--profile-primary);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--profile-primary) 10%, transparent);
  outline: none;
}

.profile-password-card__row button {
  min-height: 42px;
  border: 1px solid var(--profile-primary);
  border-radius: 10px;
  background: var(--profile-primary);
  color: #ffffff;
  padding: 0 18px;
  font: inherit;
  font-size: 14px;
  font-weight: 650;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.profile-password-card__row button:hover,
.profile-password-card__row button:focus-visible {
  border-color: var(--primary-hover);
  background: var(--primary-hover);
  outline: none;
}

.profile-password-card__row button:disabled {
  cursor: wait;
  opacity: 0.7;
}

@media (max-width: 1199px) {
  .profile-shell {
    width: min(100% - 40px, 1100px);
    grid-template-columns: 220px minmax(0, 1fr);
  }

  .profile-hero__scenery {
    width: 42%;
  }
}

@media (max-width: 860px) {
  .profile-page {
    padding-top: 26px;
  }

  .profile-shell {
    grid-template-columns: 1fr;
  }

  .profile-sidebar {
    position: static;
    grid-template-columns: minmax(180px, 0.8fr) minmax(0, 2fr);
    align-items: center;
  }

  .profile-sidebar__identity {
    border-right: 1px solid var(--profile-border);
    border-bottom: 0;
    padding: 5px 15px 5px 5px;
  }

  .profile-sidebar__nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .profile-nav-item {
    min-height: 42px;
    justify-content: center;
    padding: 0 8px;
  }

  .profile-nav-item--active::before,
  .profile-nav-item.router-link-active::before {
    left: 0;
    height: 20px;
  }
}

@media (max-width: 640px) {
  .profile-page {
    padding-bottom: 52px;
  }

  .profile-shell {
    width: min(100% - 28px, 640px);
    gap: 16px;
  }

  .profile-sidebar {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .profile-sidebar__identity {
    border-right: 0;
    border-bottom: 1px solid var(--profile-border);
    padding: 4px 6px 14px;
  }

  .profile-sidebar__nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .profile-nav-item {
    justify-content: flex-start;
  }

  .profile-hero {
    min-height: 0;
    padding: 24px 20px;
  }

  .profile-hero__scenery {
    right: -70px;
    width: 78%;
    opacity: 0.15;
  }

  .profile-hero__motto {
    margin-left: 0;
  }

  .profile-card {
    gap: 17px;
    padding: 20px;
  }

  .profile-card__header,
  .history-heading {
    align-items: flex-start;
  }

  .profile-card__title {
    align-items: flex-start;
  }

  .profile-card__action {
    padding: 0;
  }

  .survey-grid,
  .profile-password-card__row {
    grid-template-columns: 1fr;
  }

  .profile-favorites-card__entry {
    min-height: 0;
    grid-template-columns: 46px minmax(0, 1fr);
    gap: 12px;
  }

  .profile-favorites-card__star {
    width: 46px;
    height: 46px;
  }

  .profile-primary-link {
    grid-column: 1 / -1;
    width: 100%;
  }

  .history-error {
    align-items: flex-start;
    flex-direction: column;
  }

  .history-error button,
  .profile-password-card__row button {
    width: 100%;
  }
}
</style>
