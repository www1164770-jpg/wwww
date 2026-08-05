<template>
  <div class="admin-page">
    <AppHeader />
    <main class="admin-shell">
      <aside class="admin-sidebar">
        <h1>后台管理</h1>
        <RouterLink to="/admin/dashboard" exact-active-class="active"
          >数据概览</RouterLink
        >
        <RouterLink to="/admin/sites" exact-active-class="active"
          >网站管理</RouterLink
        >
        <RouterLink to="/admin/categories" exact-active-class="active"
          >分类管理</RouterLink
        >
        <RouterLink to="/admin/tags" exact-active-class="active"
          >标签管理</RouterLink
        >
        <RouterLink to="/admin/users" exact-active-class="active"
          >用户管理</RouterLink
        >
        <RouterLink to="/admin/comments" exact-active-class="active"
          >评论审核</RouterLink
        >
        <RouterLink to="/admin/crawler-review" exact-active-class="active"
          >爬虫审核</RouterLink
        >
        <RouterLink to="/admin/questionnaires" exact-active-class="active"
          >问卷管理</RouterLink
        >
        <RouterLink to="/admin/recommend-rules" exact-active-class="active"
          >推荐规则</RouterLink
        >
        <RouterLink to="/admin/settings" exact-active-class="active"
          >后台设置</RouterLink
        >
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

a.active,
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
