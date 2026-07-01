<template>
  <header class="app-header">
    <div class="header-inner">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">智</span>
        <span>智慧导航</span>
      </RouterLink>

      <nav class="nav-links" aria-label="主导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/categories">分类导航</RouterLink>
        <RouterLink to="/search?q=AI 工具">AI工具</RouterLink>
        <RouterLink to="/#career">职业推荐</RouterLink>
        <RouterLink to="/search?sort=hot">热门网站</RouterLink>
        <RouterLink to="/search?sort=latest">最新收录</RouterLink>
        <RouterLink v-if="loggedIn" to="/favorites">我的收藏</RouterLink>
      </nav>

      <div class="actions">
        <RouterLink v-if="loggedIn" class="avatar" to="/profile">
          {{ initials }}
        </RouterLink>
        <template v-else>
          <RouterLink class="login-link" to="/login">登录</RouterLink>
          <RouterLink class="primary" to="/register">注册</RouterLink>
        </template>
      </div>
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
  border-bottom: 1px solid #edf2f7;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(16px);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  width: min(1200px, calc(100% - 40px));
  height: 72px;
  margin: 0 auto;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--color-heading);
  font-size: 18px;
  font-weight: 850;
  text-decoration: none;
  white-space: nowrap;
}

.brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 13px;
  color: #ffffff;
  background: linear-gradient(135deg, var(--color-primary), #ff9b75);
  box-shadow: 0 12px 24px rgba(255, 112, 88, 0.2);
}

.nav-links,
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-links {
  justify-content: center;
  flex: 1;
}

a {
  color: var(--color-text);
  text-decoration: none;
  font-size: 14px;
  font-weight: 700;
  transition:
    color var(--transition),
    background var(--transition),
    transform var(--transition);
}

.nav-links a {
  min-height: 40px;
  border-radius: var(--radius-pill);
  padding: 10px 14px;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  color: var(--color-primary);
  background: var(--color-soft-orange);
}

.login-link {
  min-height: 40px;
  padding: 10px 12px;
}

.primary,
.avatar {
  display: inline-grid;
  min-height: 40px;
  place-items: center;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 0 18px;
  box-shadow: 0 12px 24px rgba(255, 112, 88, 0.18);
}

.primary:hover,
.avatar:hover {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
}

.avatar {
  width: 42px;
  height: 42px;
  padding: 0;
}

@media (max-width: 900px) {
  .header-inner {
    width: min(100% - 28px, 1200px);
    height: auto;
    min-height: 72px;
    flex-wrap: wrap;
    padding: 12px 0;
  }

  .nav-links {
    order: 3;
    flex-basis: 100%;
    justify-content: flex-start;
    overflow-x: auto;
    padding-bottom: 2px;
  }
}
</style>
