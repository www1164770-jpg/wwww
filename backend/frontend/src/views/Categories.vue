<template>
  <div class="page">
    <AppHeader />
    <main>
      <h1>Categories</h1>
      <div class="grid">
        <RouterLink
          v-for="category in roots"
          :key="category.id"
          :to="`/category/${category.id}`"
        >
          <span>{{ category.icon || "#" }}</span>
          <strong>{{ category.name }}</strong>
        </RouterLink>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AppHeader from "../components/layout/AppHeader.vue";
import { categoryAPI } from "../utils/api";

const categories = ref([]);
const roots = computed(() =>
  categories.value.filter((item) => !item.parent_id),
);

onMounted(async () => {
  const response = await categoryAPI.getCategories();
  categories.value = response.data?.data || [];
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f8fafc;
}
main {
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
