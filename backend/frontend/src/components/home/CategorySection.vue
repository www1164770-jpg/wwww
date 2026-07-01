<template>
  <section class="home-section category-section">
    <aside class="category-copy">
      <p>热门分类</p>
      <h2>热门工具分类</h2>
      <span>按学习、创作、开发和效率场景浏览高质量 AI 工具。</span>
      <div class="category-menu">
        <RouterLink
          v-for="category in categories"
          :key="category.id"
          :to="`/category/${category.id}`"
        >
          {{ category.name }}
        </RouterLink>
      </div>
    </aside>

    <div v-if="categories.length" class="category-grid">
      <RouterLink
        v-for="category in categories"
        :key="category.id"
        class="category-card"
        :to="`/category/${category.id}`"
      >
        <span>{{ category.icon || "AI" }}</span>
        <strong>{{ category.name }}</strong>
        <small>查看该分类下的精选网站资源</small>
      </RouterLink>
    </div>
    <EmptyState
      v-else
      title="暂无分类"
      description="分类数据加载后会展示在这里。"
    />
  </section>
</template>

<script setup>
import EmptyState from "../common/EmptyState.vue";

defineProps({ categories: { type: Array, default: () => [] } });
</script>

<style scoped>
.category-section {
  display: grid;
  grid-template-columns: minmax(220px, 300px) 1fr;
  gap: 34px;
  padding: 92px 0 40px;
}

.category-copy {
  align-self: start;
}

.category-copy p {
  margin: 0 0 8px;
  color: var(--color-primary);
  font-weight: 800;
}

.category-copy h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(32px, 4vw, 44px);
  line-height: 1.12;
}

.category-copy > span {
  display: block;
  margin-top: 14px;
  color: var(--color-text);
  line-height: 1.7;
}

.category-menu {
  display: grid;
  gap: 8px;
  margin-top: 28px;
}

.category-menu a {
  border-radius: var(--radius-pill);
  padding: 11px 16px;
  color: var(--color-text);
  text-decoration: none;
  font-weight: 750;
}

.category-menu a:hover,
.category-menu a:first-child {
  color: var(--color-primary);
  background: var(--color-soft-orange);
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.category-card {
  display: grid;
  align-content: start;
  gap: 12px;
  min-height: 180px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 20px;
  color: var(--color-heading);
  text-decoration: none;
  transition:
    transform var(--transition),
    box-shadow var(--transition),
    border-color var(--transition);
}

.category-card:hover {
  border-color: rgba(255, 112, 88, 0.34);
  transform: translateY(-4px);
  box-shadow: var(--shadow-card);
}

.category-card span {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 16px;
  color: var(--color-primary);
  background: var(--color-soft-orange);
  font-weight: 850;
}

.category-card strong {
  font-size: 18px;
}

.category-card small {
  color: var(--color-muted);
  line-height: 1.55;
}

@media (max-width: 980px) {
  .category-section {
    grid-template-columns: 1fr;
  }

  .category-menu {
    display: flex;
    flex-wrap: wrap;
  }
}

@media (max-width: 720px) {
  .category-section {
    padding-top: 64px;
  }

  .category-grid {
    grid-template-columns: 1fr;
  }
}
</style>
