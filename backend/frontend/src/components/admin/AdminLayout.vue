<template>
  <div class="admin-page">
    <AppHeader />
    <main class="admin-shell">
      <aside class="admin-sidebar">
        <h1>后台管理</h1>
        <RouterLink to="/admin/dashboard">数据概览</RouterLink>
        <RouterLink to="/admin/sites">网站管理</RouterLink>
        <RouterLink to="/admin/categories">分类管理</RouterLink>
        <RouterLink to="/admin/tags">标签管理</RouterLink>
        <RouterLink to="/admin/users">用户管理</RouterLink>
        <RouterLink to="/admin/comments">评论审核</RouterLink>
      </aside>
      <section class="admin-content">
        <slot></slot>
      </section>
    </main>
  </div>
</template>

<script setup>
import AppHeader from "../layout/AppHeader.vue";
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: var(--color-soft);
}

.admin-shell {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 20px;
  width: min(1240px, calc(100% - 40px));
  margin: 36px auto 72px;
}

.admin-sidebar,
.admin-content {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 20px;
  box-shadow: var(--shadow-soft);
}

.admin-sidebar {
  display: grid;
  align-content: start;
  gap: 10px;
}

h1 {
  margin: 0 0 14px;
  color: var(--color-heading);
  font-size: 22px;
}

a {
  border-radius: var(--radius-pill);
  color: var(--color-text);
  padding: 10px 14px;
  text-decoration: none;
  font-weight: 750;
}

a.router-link-active,
a:hover {
  background: var(--color-soft-orange);
  color: var(--color-primary);
}

@media (max-width: 860px) {
  .admin-shell {
    grid-template-columns: 1fr;
  }
}
</style>
