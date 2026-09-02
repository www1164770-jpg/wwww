<template>
  <div class="page">
    <AppHeader />
    <main>
      <aside class="profile-menu">
        <div class="user-card">
          <strong>{{ profile.user?.username || "用户" }}</strong>
          <span>{{ profile.user?.email || "暂无邮箱" }}</span>
          <small>{{ roleText(profile.user?.role) }}</small>
        </div>
        <nav aria-label="个人中心菜单">
          <RouterLink to="/personalization">个性化设置</RouterLink>
          <a href="#questionnaire">我的问卷</a>
          <a href="#favorites">我的收藏</a>
          <a href="#history">浏览历史</a>
          <a href="#password">修改密码</a>
        </nav>
      </aside>

      <section class="content">
        <LoadingState v-if="loading" text="正在加载个人中心..." />
        <EmptyState
          v-else-if="error"
          title="个人中心加载失败"
          :description="error"
        />
        <template v-else>
          <section id="questionnaire" class="panel">
            <div class="section-head">
              <AnimatedPageTitle>个人中心</AnimatedPageTitle>
              <p>管理你的职业画像、收藏记录和账号安全。</p>
            </div>
            <h2>我的问卷</h2>
            <div v-if="hasQuestionnaire" class="questionnaire-summary">
              <span>职业：{{ labelText(profile.profile?.occupation) }}</span>
              <span
                >能力水平：{{ labelText(profile.profile?.skill_level) }}</span
              >
              <span>兴趣：{{ listText(profile.profile?.interests) }}</span>
              <span>偏好：{{ listText(profile.profile?.preferences) }}</span>
              <span>用途：{{ listText(profile.profile?.purposes) }}</span>
            </div>
            <EmptyState
              v-else
              title="暂无问卷信息"
              description="完成职业问卷后，系统会为你推荐更适合的资源。"
              action-text="填写问卷"
              action-to="/questionnaire"
            />
            <RouterLink class="text-action" to="/questionnaire"
              >更新问卷</RouterLink
            >
          </section>

          <section id="favorites" class="panel">
            <h2>我的收藏</h2>
            <EmptyState
              title="收藏入口"
              description="进入收藏页查看和管理你保存的网站资源。"
              action-text="查看收藏"
              action-to="/favorites"
            />
          </section>

          <section id="history" class="panel">
            <div class="history-heading">
              <h2>浏览历史</h2>
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

          <section id="password" class="panel">
            <h2>修改密码</h2>
            <div class="password-row">
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
import { ExternalLink, RotateCw, Trash2 } from "lucide-vue-next";
import { computed, onMounted, ref } from "vue";
import AnimatedPageTitle from "../components/common/AnimatedPageTitle.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SiteLogo from "../components/site/SiteLogo.vue";
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
.page {
  min-height: 100vh;
  background: transparent;
}

main {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 24px;
  width: min(1120px, calc(100% - 40px));
  margin: 42px auto 78px;
  align-items: start;
}

.profile-menu {
  position: sticky;
  top: 92px;
  display: grid;
  gap: 16px;
}

.user-card,
.panel {
  border: 1px solid var(--app-card-border);
  border-radius: var(--radius-card);
  background: var(--app-panel-bg);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
  padding: 22px;
  box-shadow: var(--app-card-shadow);
}

.user-card {
  display: grid;
  gap: 8px;
}

.user-card strong {
  color: var(--app-text-primary);
  font-size: 22px;
}

.user-card span,
.user-card small,
.section-head p {
  color: var(--app-text-secondary);
  line-height: 1.6;
}

nav {
  display: grid;
  gap: 8px;
  border: 1px solid var(--app-card-border);
  border-radius: var(--radius-card);
  background: var(--app-panel-bg);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
  padding: 12px;
  box-shadow: var(--app-card-shadow);
}

nav a,
.text-action {
  border-radius: var(--radius-pill);
  color: var(--app-text-primary);
  padding: 11px 14px;
  text-decoration: none;
  font-weight: 800;
  transition:
    background var(--transition),
    color var(--transition),
    transform var(--transition);
}

nav a:hover,
nav a:focus-visible,
.text-action:hover,
.text-action:focus-visible {
  background: var(--app-card-hover-bg);
  color: var(--color-primary);
  transform: translateY(-1px);
  outline: none;
}

.content,
.panel {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.section-head {
  display: grid;
  gap: 8px;
}

h1,
h2 {
  margin: 0;
  color: var(--app-text-primary);
}

h1 {
  font-size: clamp(32px, 5vw, 46px);
}

h2 {
  font-size: 22px;
}

.questionnaire-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.questionnaire-summary span {
  border: 1px solid var(--app-card-border);
  border-radius: 16px;
  background: var(--app-control-bg);
  color: var(--app-text-secondary);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 12px;
  line-height: 1.5;
}

.password-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) auto;
  gap: 12px;
  align-items: end;
}

.history-heading,
.history-title-row,
.history-meta {
  display: flex;
  align-items: center;
}

.history-heading {
  justify-content: space-between;
  gap: 16px;
}

.history-clear,
.history-error button {
  display: inline-flex;
  width: auto;
  min-height: 38px;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--app-card-border);
  border-radius: 6px;
  background: var(--app-control-bg);
  color: var(--app-text-primary);
  padding: 0 12px;
  box-shadow: none;
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
  border-left: 3px solid #d69e2e;
  background: var(--app-control-bg);
  color: var(--app-text-primary);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 11px 14px;
}

.history-list {
  display: grid;
  gap: 10px;
}

.history-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 40px;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--app-card-border);
  border-radius: 8px;
  background: var(--app-control-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 10px;
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

.history-title-row {
  min-width: 0;
  gap: 7px;
}

.history-title-row strong {
  overflow: hidden;
  color: var(--app-text-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-title-row svg {
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
  color: var(--color-primary);
}

.history-description {
  overflow: hidden;
  color: var(--app-text-secondary);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-meta {
  flex-wrap: wrap;
  gap: 8px;
  color: var(--app-text-muted);
  font-size: 12px;
}

.history-meta b {
  color: var(--color-primary-dark);
}

.history-delete {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--app-text-muted);
  padding: 0;
  box-shadow: none;
}

.history-delete:hover,
.history-delete:focus-visible {
  background: var(--app-card-hover-bg);
  color: #c53030;
}

label {
  display: grid;
  gap: 8px;
  color: var(--app-text-primary);
  font-weight: 750;
}

input {
  min-width: 0;
  border: 1px solid var(--app-card-border);
  border-radius: 14px;
  background: var(--app-input-bg);
  color: var(--app-input-text);
  padding: 12px;
}

button {
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 13px 18px;
  font-weight: 850;
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.18);
}

button:hover,
button:focus-visible {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  outline: none;
}

button:disabled {
  cursor: wait;
  opacity: 0.72;
  transform: none;
}

@media (max-width: 900px) {
  main {
    grid-template-columns: 1fr;
  }

  .profile-menu {
    position: static;
  }

  nav {
    grid-template-columns: repeat(4, max-content);
    overflow-x: auto;
  }
}

@media (max-width: 768px) {
  main {
    width: min(100% - 28px, 1120px);
    margin-top: 32px;
  }

  .questionnaire-summary,
  .password-row {
    grid-template-columns: 1fr;
  }

  button {
    width: 100%;
  }
}
</style>
