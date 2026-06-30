<template>
  <header class="app-header">
    <RouterLink class="brand" to="/">智汇 AI 导航</RouterLink>
    <nav class="nav-links">
      <RouterLink to="/">首页</RouterLink>
      <RouterLink to="/categories">分类导航</RouterLink>
      <RouterLink to="/search?q=AI 工具">AI 工具</RouterLink>
      <RouterLink to="/search?sort=hot">热门</RouterLink>
      <RouterLink to="/search?sort=latest">最新</RouterLink>
      <RouterLink v-if="loggedIn" to="/favorites">我的收藏</RouterLink>
    </nav>
    <div class="actions">
      <RouterLink v-if="loggedIn" class="avatar" to="/profile">{{
        initials
      }}</RouterLink>
      <template v-else>
        <RouterLink to="/login">登录</RouterLink>
        <RouterLink class="primary" to="/register">注册</RouterLink>
      </template>
    </div>
  </header>
</template>

<script setup>
import { computed } from "vue";

const loggedIn = computed(() => Boolean(localStorage.getItem("access_token")));
const user = computed(() => {
  try {
    return JSON.parse(localStorage.getItem("user_info") || "{}");
  } catch {
    return {};
  }
});
const initials = computed(() =>
  (user.value.username || "U").slice(0, 1).toUpperCase(),
);
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px clamp(18px, 5vw, 64px);
  border-bottom: 1px solid #e5e7eb;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
}
.brand {
  color: #111827;
  font-size: 20px;
  font-weight: 800;
  text-decoration: none;
}
.nav-links,
.actions {
  display: flex;
  align-items: center;
  gap: 14px;
}
a {
  color: #4b5563;
  text-decoration: none;
  font-weight: 650;
}
.primary,
.avatar {
  border-radius: 999px;
  background: #111827;
  color: #fff;
  padding: 9px 14px;
}
.avatar {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  padding: 0;
}
@media (max-width: 780px) {
  .app-header,
  .nav-links {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
