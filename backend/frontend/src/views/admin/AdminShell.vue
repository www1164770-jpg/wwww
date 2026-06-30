<template>
  <div class="page">
    <AppHeader />
    <main>
      <aside>
        <RouterLink to="/admin/dashboard">Dashboard</RouterLink>
        <RouterLink to="/admin/sites">Sites</RouterLink>
        <RouterLink to="/admin/categories">Categories</RouterLink>
        <RouterLink to="/admin/tags">Tags</RouterLink>
        <RouterLink to="/admin/users">Users</RouterLink>
        <RouterLink to="/admin/comments">Comments</RouterLink>
      </aside>
      <section class="panel">
        <slot></slot>
      </section>
    </main>
  </div>
</template>

<script setup>
import AppHeader from "../../components/layout/AppHeader.vue";
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f8fafc;
}
main {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 20px;
  width: min(1180px, calc(100% - 36px));
  margin: 36px auto;
}
aside,
.panel {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 18px;
}
aside {
  display: grid;
  align-content: start;
  gap: 8px;
}
a {
  color: #111827;
  text-decoration: none;
  font-weight: 750;
}
a.router-link-active {
  color: #2563eb;
}
@media (max-width: 820px) {
  main {
    grid-template-columns: 1fr;
  }
}
</style>
