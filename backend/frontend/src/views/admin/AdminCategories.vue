<template>
  <AdminShell>
    <h1>Categories</h1>
    <LoadingState v-if="loading" title="Loading categories" />
    <div v-else-if="categories.length" class="table">
      <div v-for="category in categories" :key="category.id" class="row">
        <span>{{ category.name }}</span>
        <small>#{{ category.id }}</small>
      </div>
    </div>
    <EmptyState
      v-else
      title="No categories"
      description="No categories were found."
    />
  </AdminShell>
</template>

<script setup>
import { onMounted, ref } from "vue";
import EmptyState from "../../components/common/EmptyState.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";
import AdminShell from "./AdminShell.vue";
import { readData } from "./adminHelpers";

const loading = ref(false);
const categories = ref([]);

onMounted(async () => {
  loading.value = true;
  try {
    const response = await adminAPI.getCategories();
    categories.value = readData(response);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
@import "./adminTable.css";
</style>
