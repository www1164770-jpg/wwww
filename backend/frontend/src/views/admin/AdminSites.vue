<template>
  <AdminShell>
    <h1>Sites</h1>
    <LoadingState v-if="loading" title="Loading sites" />
    <div v-else-if="sites.length" class="table">
      <div v-for="site in sites" :key="site.id" class="row">
        <span>{{ site.name }}</span>
        <a :href="site.url" target="_blank" rel="noreferrer">Visit</a>
      </div>
    </div>
    <EmptyState v-else title="No sites" description="No sites were found." />
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
const sites = ref([]);

onMounted(async () => {
  loading.value = true;
  try {
    const response = await adminAPI.getSites({ per_page: 50 });
    sites.value = readData(response);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
@import "./adminTable.css";
</style>
