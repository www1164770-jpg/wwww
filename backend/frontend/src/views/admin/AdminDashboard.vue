<template>
  <AdminShell>
    <h1>Dashboard</h1>
    <LoadingState
      v-if="loading"
      title="Loading dashboard"
      description="Fetching admin overview."
    />
    <div v-else class="stats">
      <div>
        <strong>{{ dashboard.users || users.length || 0 }}</strong>
        <span>Users</span>
      </div>
      <div>
        <strong>{{ dashboard.sites || sites.length || 0 }}</strong>
        <span>Sites</span>
      </div>
      <div>
        <strong>{{ dashboard.categories || categories.length || 0 }}</strong>
        <span>Categories</span>
      </div>
    </div>
  </AdminShell>
</template>

<script setup>
import { onMounted, ref } from "vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";
import AdminShell from "./AdminShell.vue";
import { readData } from "./adminHelpers";

const loading = ref(false);
const dashboard = ref({});
const sites = ref([]);
const categories = ref([]);
const users = ref([]);

onMounted(async () => {
  loading.value = true;
  try {
    const [dashboardRes, siteRes, categoryRes, userRes] = await Promise.all([
      adminAPI.getDashboard().catch(() => ({ data: { data: {} } })),
      adminAPI.getSites({ per_page: 50 }).catch(() => ({ data: { data: [] } })),
      adminAPI.getCategories().catch(() => ({ data: { data: [] } })),
      adminAPI.getUsers().catch(() => ({ data: { data: [] } })),
    ]);
    dashboard.value = dashboardRes.data?.data || dashboardRes.data || {};
    sites.value = readData(siteRes);
    categories.value = readData(categoryRes);
    users.value = readData(userRes);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
h1 {
  margin-top: 0;
}
.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.stats div {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}
.stats strong {
  display: block;
  font-size: 34px;
}
@media (max-width: 720px) {
  .stats {
    grid-template-columns: 1fr;
  }
}
</style>
