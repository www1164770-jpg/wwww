<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="hero">
        <h1>分类导航</h1>
        <p>按场景快速找到适合学习、工作、创作和项目开发的 AI 工具。</p>
        <SearchBar
          v-model="keyword"
          :navigate-on-submit="false"
          placeholder="搜索分类名称..."
        />
      </section>
      <LoadingState v-if="loading" text="正在加载分类..." />
      <div v-else-if="filteredRoots.length" class="grid">
        <RouterLink
          v-for="category in filteredRoots"
          :key="category.id"
          :to="`/category/${category.id}`"
        >
          <span>{{ category.icon || "AI" }}</span>
          <strong>{{ category.name }}</strong>
          <small>查看该分类下的精选工具</small>
        </RouterLink>
      </div>
      <EmptyState v-else title="暂无分类" description="没有找到匹配的分类。" />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SearchBar from "../components/common/SearchBar.vue";
import { categoryAPI } from "../utils/api";

const categories = ref([]);
const keyword = ref("");
const loading = ref(false);
const roots = computed(() =>
  categories.value.filter((item) => !item.parent_id),
);
const filteredRoots = computed(() => {
  const value = keyword.value.trim().toLowerCase();
  if (!value) return roots.value;
  return roots.value.filter((item) =>
    String(item.name || "")
      .toLowerCase()
      .includes(value),
  );
});

onMounted(async () => {
  loading.value = true;
  try {
    const response = await categoryAPI.getCategories();
    categories.value = response.data?.data || response.data || [];
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #ffffff;
}

main {
  display: grid;
  gap: 24px;
  width: min(1120px, calc(100% - 40px));
  margin: 44px auto 72px;
}

.hero {
  display: grid;
  justify-items: center;
  gap: 18px;
  border-radius: var(--radius-large);
  background:
    radial-gradient(
      circle at 10% 20%,
      rgba(191, 245, 237, 0.35),
      transparent 30%
    ),
    radial-gradient(
      circle at 90% 35%,
      rgba(255, 112, 88, 0.14),
      transparent 30%
    ),
    #ffffff;
  padding: clamp(34px, 6vw, 70px);
  text-align: center;
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(38px, 6vw, 60px);
  line-height: 1.08;
}

.hero p {
  max-width: 640px;
  margin: 0;
  color: var(--color-text);
  line-height: 1.7;
}

.hero :deep(.search-bar) {
  max-width: 680px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 16px;
}

.grid a {
  display: grid;
  gap: 12px;
  min-height: 170px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  color: var(--color-heading);
  padding: 20px;
  text-decoration: none;
  transition:
    transform var(--transition),
    box-shadow var(--transition),
    border-color var(--transition);
}

.grid a:hover {
  border-color: rgba(255, 112, 88, 0.34);
  transform: translateY(-4px);
  box-shadow: var(--shadow-card);
}

.grid span {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 16px;
  background: var(--color-soft-orange);
  color: var(--color-primary);
  font-weight: 850;
}

.grid small {
  color: var(--color-muted);
}
</style>
