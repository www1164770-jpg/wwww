<template>
  <div class="page">
    <AppHeader />
    <main>
      <h1>Categories</h1>
      <SearchBar
        v-model="keyword"
        :navigate-on-submit="false"
        placeholder="Search categories..."
      />
      <LoadingState
        v-if="loading"
        title="Loading categories"
        description="Fetching category navigation."
      />
      <div v-else-if="filteredRoots.length" class="grid">
        <RouterLink
          v-for="category in filteredRoots"
          :key="category.id"
          :to="`/category/${category.id}`"
        >
          <span>{{ category.icon || "#" }}</span>
          <strong>{{ category.name }}</strong>
        </RouterLink>
      </div>
      <EmptyState
        v-else
        title="No categories"
        description="No matching category was found."
      />
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
  background: #f8fafc;
}
main {
  display: grid;
  gap: 18px;
  width: min(1100px, calc(100% - 36px));
  margin: 36px auto;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
}
a {
  display: flex;
  gap: 12px;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  text-decoration: none;
}
span {
  color: #2563eb;
}
</style>
