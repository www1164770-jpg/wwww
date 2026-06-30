<template>
  <header class="app-header">
    <RouterLink class="brand" to="/">AI Nav</RouterLink>
    <nav class="nav-links">
      <RouterLink to="/">Home</RouterLink>
      <RouterLink to="/categories">Categories</RouterLink>
      <RouterLink to="/search?q=AI tools">AI Tools</RouterLink>
      <RouterLink to="/search?sort=hot">Hot</RouterLink>
      <RouterLink to="/search?sort=latest">Latest</RouterLink>
      <RouterLink v-if="loggedIn" to="/favorites">Favorites</RouterLink>
    </nav>
    <div class="actions">
      <RouterLink v-if="loggedIn" class="avatar" to="/profile">{{
        initials
      }}</RouterLink>
      <template v-else>
        <RouterLink to="/login">Login</RouterLink>
        <RouterLink class="primary" to="/register">Register</RouterLink>
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
