<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="hero">
        <div>
          <AnimatedPageTitle>分类导航</AnimatedPageTitle>
          <p>按行业和使用场景快速找到高质量网站资源。</p>
        </div>
        <SearchBar
          v-model="keyword"
          :navigate-on-submit="false"
          placeholder="搜索分类名称..."
        />
      </section>

      <LoadingState v-if="loading" text="正在加载分类..." />
      <EmptyState v-else-if="error" title="分类加载失败" :description="error" />
      <div v-else-if="filteredRoots.length" class="grid">
        <RouterLink
          v-for="category in filteredRoots"
          :key="category.id"
          class="category-card"
          :to="`/category/${category.id}`"
        >
          <span class="category-icon">{{ category.icon || "AI" }}</span>
          <strong>{{ category.name }}</strong>
          <small>{{
            category.description || "查看该分类下的精选网站资源"
          }}</small>
          <span class="card-action">查看资源</span>
        </RouterLink>
      </div>
      <EmptyState
        v-else
        title="暂无分类"
        description="可以尝试更换关键词或稍后再来查看。"
      />
    </main>
    <AppFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AnimatedPageTitle from "../components/common/AnimatedPageTitle.vue";
import AppFooter from "../components/layout/AppFooter.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SearchBar from "../components/common/SearchBar.vue";
import { categoryAPI, unwrapResponse } from "../utils/api";
import { errorToast } from "../utils/toast";

const categories = ref([]);
const keyword = ref("");
const loading = ref(false);
const error = ref("");
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

function flattenCategories(value) {
  const source = Array.isArray(value)
    ? value
    : value?.items || value?.categories || [];
  const result = new Map();
  const visit = (item) => {
    if (!item || result.has(item.id)) return;
    result.set(item.id, item);
    (item.children || []).forEach(visit);
  };
  source.forEach(visit);
  return [...result.values()];
}

onMounted(async () => {
  loading.value = true;
  error.value = "";
  try {
    const response = await categoryAPI.getCategories();
    categories.value = flattenCategories(unwrapResponse(response));
  } catch (err) {
    error.value = err.response?.data?.msg || "分类加载失败，请稍后重试";
    errorToast(error.value);
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
  gap: 28px;
  width: min(1120px, calc(100% - 40px));
  min-width: 0;
  margin: 48px auto 78px;
}

.hero {
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr);
  justify-items: center;
  gap: 22px;
  border-radius: 24px;
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
  padding: clamp(38px, 6vw, 76px);
  text-align: center;
  box-shadow: var(--app-card-shadow);
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(38px, 6vw, 60px);
  line-height: 1.08;
}

.hero p {
  max-width: 640px;
  margin: 12px 0 0;
  color: #718096;
  line-height: 1.7;
}

.hero :deep(.search-bar) {
  width: 100%;
  max-width: 700px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(240px, 100%), 1fr));
  gap: 18px;
}

.category-card {
  display: grid;
  gap: 14px;
  min-width: 0;
  min-height: 210px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  color: var(--color-heading);
  padding: 22px;
  text-decoration: none;
  box-shadow: var(--app-card-shadow);
  transition:
    transform var(--transition),
    box-shadow var(--transition),
    border-color var(--transition);
}

.category-card:hover,
.category-card:focus-visible {
  border-color: rgba(255, 112, 88, 0.34);
  transform: translateY(-5px);
  box-shadow: var(--app-card-hover-shadow);
  outline: none;
}

.category-icon {
  position: relative;
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  border-radius: 18px;
  background: var(--color-soft-orange);
  color: var(--color-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 850;
  letter-spacing: 0;
  box-shadow: inset 0 0 0 1px rgba(255, 112, 88, 0.16);
}

.category-icon::after {
  position: absolute;
  right: 10px;
  bottom: 9px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-primary);
  content: "";
}

strong {
  font-size: 20px;
}

small {
  color: #718096;
  line-height: 1.65;
}

.card-action {
  display: inline-grid;
  width: max-content;
  min-height: 38px;
  place-items: center;
  margin-top: auto;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 0 15px;
  font-size: 13px;
  font-weight: 850;
}

@media (max-width: 768px) {
  main {
    width: min(100% - 28px, 1120px);
    margin-top: 32px;
  }
}
</style>
