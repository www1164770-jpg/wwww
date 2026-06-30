<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="panel">
        <h1>个人中心</h1>
        <div class="profile-row">
          <strong>{{ profile.user?.username || "用户" }}</strong>
          <span>{{ profile.user?.email }}</span>
          <span>{{ roleText(profile.user?.role) }}</span>
        </div>
      </section>
      <section class="panel">
        <h2>我的问卷</h2>
        <div class="questionnaire-summary">
          <span>职业：{{ labelText(profile.profile?.occupation) }}</span>
          <span>能力水平：{{ labelText(profile.profile?.skill_level) }}</span>
          <span>兴趣：{{ listText(profile.profile?.interests) }}</span>
          <span>偏好：{{ listText(profile.profile?.preferences) }}</span>
          <span>用途：{{ listText(profile.profile?.purposes) }}</span>
        </div>
        <RouterLink to="/questionnaire">更新问卷</RouterLink>
      </section>
      <section class="panel">
        <h2>我的推荐</h2>
        <SiteList
          :sites="profile.recommendations || []"
          @favorite="favorite"
          @visit="visit"
        />
      </section>
      <section class="panel">
        <h2>我的收藏</h2>
        <RouterLink to="/favorites">查看收藏</RouterLink>
      </section>
      <section class="panel">
        <h2>浏览历史</h2>
        <EmptyState
          title="暂无浏览历史"
          description="访问过的网站后续会在这里展示。"
        />
      </section>
      <section class="panel">
        <h2>修改密码</h2>
        <div class="password-row">
          <input v-model="oldPassword" type="password" placeholder="旧密码" />
          <input v-model="newPassword" type="password" placeholder="新密码" />
          <button @click="changePassword">更新</button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import SiteList from "../components/site/SiteList.vue";
import { favoriteAPI, siteAPI, userAPI } from "../utils/api";

const profile = ref({});
const oldPassword = ref("");
const newPassword = ref("");

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
  const response = await userAPI.getProfile();
  profile.value = response.data?.data || {};
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
  gap: 18px;
  width: min(1060px, calc(100% - 36px));
  margin: 36px auto;
}
.panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 22px;
}
.profile-row,
.password-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}
input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 11px;
}
button {
  border: 0;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  padding: 11px 14px;
  font-weight: 800;
}
.questionnaire-summary {
  display: grid;
  gap: 8px;
  color: #4b5563;
}
</style>
