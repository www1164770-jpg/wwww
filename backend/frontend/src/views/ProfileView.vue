<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="panel">
        <h1>Profile</h1>
        <div class="profile-row">
          <strong>{{ profile.user?.username || "User" }}</strong>
          <span>{{ profile.user?.email }}</span>
          <span>{{ profile.user?.role }}</span>
        </div>
      </section>
      <section class="panel">
        <h2>My questionnaire</h2>
        <pre>{{ profile.profile || {} }}</pre>
        <RouterLink to="/questionnaire">Update questionnaire</RouterLink>
      </section>
      <section class="panel">
        <h2>My recommendations</h2>
        <SiteList
          :sites="profile.recommendations || []"
          @favorite="favorite"
          @visit="visit"
        />
      </section>
      <section class="panel">
        <h2>My favorites</h2>
        <RouterLink to="/favorites">View favorites</RouterLink>
      </section>
      <section class="panel">
        <h2>Browsing history</h2>
        <EmptyState
          title="No browsing history"
          description="Visited sites will appear here later."
        />
      </section>
      <section class="panel">
        <h2>Change password</h2>
        <div class="password-row">
          <input
            v-model="oldPassword"
            type="password"
            placeholder="Old password"
          />
          <input
            v-model="newPassword"
            type="password"
            placeholder="New password"
          />
          <button @click="changePassword">Update</button>
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

async function load() {
  const response = await userAPI.getProfile();
  profile.value = response.data?.data || {};
}
async function favorite(site) {
  await favoriteAPI.addFavorite(site.id);
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
pre {
  white-space: pre-wrap;
  color: #4b5563;
}
</style>
