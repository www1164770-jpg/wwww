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
          <a href="#questionnaire">我的问卷</a>
          <a href="#recommendations">我的推荐</a>
          <a href="#favorites">我的收藏</a>
          <a href="#history">浏览历史</a>
          <a href="#password">修改密码</a>
        </nav>
      </aside>

      <section class="content">
        <LoadingState v-if="loading" text="正在加载个人中心..." />
        <template v-else>
          <section id="questionnaire" class="panel">
            <div class="section-head">
              <h1>个人中心</h1>
              <p>管理你的职业画像、推荐资源和账号安全。</p>
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

          <section id="recommendations" class="panel">
            <h2>我的推荐</h2>
            <SiteList
              :sites="profile.recommendations || []"
              empty-title="暂无推荐"
              empty-description="完成问卷后会在这里展示个性化推荐。"
              empty-action-text="完善问卷"
              empty-action-to="/questionnaire"
              @favorite="favorite"
              @visit="visit"
            />
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
            <h2>浏览历史</h2>
            <EmptyState
              title="暂无浏览历史"
              description="访问过的网站后续会在这里展示。"
            />
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
              <button type="button" @click="changePassword">更新</button>
            </div>
          </section>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SiteList from "../components/site/SiteList.vue";
import { favoriteAPI, siteAPI, userAPI } from "../utils/api";

const profile = ref({});
const oldPassword = ref("");
const newPassword = ref("");
const loading = ref(false);
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
  try {
    const response = await userAPI.getProfile();
    profile.value = response.data?.data || {};
  } finally {
    loading.value = false;
  }
}
async function favorite(site) {
  if (site.is_favorited) {
    await favoriteAPI.removeFavorite(site.id);
    site.is_favorited = false;
  } else {
    await favoriteAPI.addFavorite(site.id);
    site.is_favorited = true;
  }
}
async function visit(site) {
  await siteAPI.recordClick(site.id).catch(() => {});
  window.open(site.url, "_blank", "noopener,noreferrer");
}
async function changePassword() {
  await userAPI.changePassword(oldPassword.value, newPassword.value);
  oldPassword.value = "";
  newPassword.value = "";
}
onMounted(load);
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f8fafc;
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
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 22px;
  box-shadow: var(--shadow-soft);
}

.user-card {
  display: grid;
  gap: 8px;
}

.user-card strong {
  color: var(--color-heading);
  font-size: 22px;
}

.user-card span,
.user-card small,
.section-head p {
  color: #718096;
  line-height: 1.6;
}

nav {
  display: grid;
  gap: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 12px;
  box-shadow: var(--shadow-soft);
}

nav a,
.text-action {
  border-radius: var(--radius-pill);
  color: var(--color-heading);
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
  background: var(--color-soft-orange);
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
  color: var(--color-heading);
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
  border-radius: 16px;
  background: var(--color-soft);
  color: var(--color-text);
  padding: 12px;
  line-height: 1.5;
}

.password-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr)) auto;
  gap: 12px;
  align-items: end;
}

label {
  display: grid;
  gap: 8px;
  color: var(--color-heading);
  font-weight: 750;
}

input {
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #ffffff;
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

@media (max-width: 900px) {
  main {
    grid-template-columns: 1fr;
  }

  .profile-menu {
    position: static;
  }

  nav {
    grid-template-columns: repeat(5, max-content);
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
