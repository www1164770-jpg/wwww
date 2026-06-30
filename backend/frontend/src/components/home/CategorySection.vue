<template>
  <section class="home-section">
    <div class="section-title">
      <p>探索</p>
      <h2>分类导航</h2>
    </div>
    <div class="category-grid">
      <RouterLink
        v-for="category in categories"
        :key="category.id"
        :to="`/category/${category.id}`"
      >
        <span>{{ category.icon || "#" }}</span>
        <strong>{{ category.name }}</strong>
      </RouterLink>
    </div>
  </section>
</template>

<script setup>
defineProps({ categories: { type: Array, default: () => [] } });
</script>

<style scoped>
.home-section {
  display: grid;
  gap: 18px;
}
.section-title p {
  margin: 0 0 6px;
  color: #2563eb;
  font-weight: 800;
}
.section-title h2 {
  margin: 0;
}
.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
a {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  color: #111827;
  text-decoration: none;
  background: #fff;
}
span {
  color: #2563eb;
}
</style>
