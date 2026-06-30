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
  background: #f8fafc;
}
.admin-shell {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 20px;
  width: min(1240px, calc(100% - 36px));
  margin: 36px auto;
}
.admin-sidebar,
.admin-content {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 18px;
}
.admin-sidebar {
  display: grid;
  align-content: start;
  gap: 10px;
}
h1 {
  margin: 0 0 12px;
  font-size: 20px;
}
a {
  border-radius: 8px;
  color: #374151;
  padding: 10px 12px;
  text-decoration: none;
  font-weight: 750;
}
a.router-link-active {
  background: #eef2ff;
  color: #1d4ed8;
}
@media (max-width: 860px) {
  .admin-shell {
    grid-template-columns: 1fr;
  }
}
</style>
