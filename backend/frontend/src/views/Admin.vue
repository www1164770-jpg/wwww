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
        <h1>{{ sectionTitle }}</h1>
        <div v-if="section === 'dashboard'" class="stats">
          <div>
            <strong>{{ dashboard.users || 0 }}</strong
            ><span>Users</span>
          </div>
          <div>
            <strong>{{ dashboard.sites || sites.length }}</strong
            ><span>Sites</span>
          </div>
          <div>
            <strong>{{ dashboard.categories || categories.length }}</strong
            ><span>Categories</span>
          </div>
        </div>
        <div v-else-if="section === 'sites'" class="table">
          <div v-for="site in sites" :key="site.id" class="row">
            <span>{{ site.name }}</span>
            <a :href="site.url" target="_blank" rel="noreferrer">Visit</a>
          </div>
        </div>
        <div v-else-if="section === 'categories'" class="table">
          <div v-for="category in categories" :key="category.id" class="row">
            <span>{{ category.name }}</span>
            <small>#{{ category.id }}</small>
          </div>
        </div>
        <div v-else-if="section === 'tags'" class="table">
          <div v-for="tag in tags" :key="tag.id" class="row">
            <span>{{ tag.name }}</span>
            <small>{{ tag.type }}</small>
          </div>
        </div>
        <div v-else-if="section === 'users'" class="table">
          <div v-for="user in users" :key="user.id" class="row">
            <span>{{ user.username || user.email }}</span>
            <small>{{ user.role || user.status }}</small>
          </div>
        </div>
        <EmptyState
          v-else
          title="Comments moderation"
          description="Comment moderation endpoint can be connected here."
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import { adminAPI } from "../utils/api";

const route = useRoute();
const dashboard = ref({});
const sites = ref([]);
const categories = ref([]);
const tags = ref([]);
const users = ref([]);

const section = computed(() => route.meta.adminSection || "dashboard");
const sectionTitle = computed(
  () => section.value[0].toUpperCase() + section.value.slice(1),
);

async function load() {
  try {
    if (section.value === "dashboard") {
      const response = await adminAPI.getDashboard();
      dashboard.value = response.data?.data || {};
    }
    if (section.value === "sites" || section.value === "dashboard") {
      const response = await adminAPI.getSites({ per_page: 50 });
      sites.value = response.data?.data?.items || response.data?.data || [];
    }
    if (section.value === "categories" || section.value === "dashboard") {
      const response = await adminAPI.getCategories();
      categories.value = response.data?.data || [];
    }
    if (section.value === "tags") {
      const response = await adminAPI.getTags();
      tags.value = response.data?.data || [];
    }
    if (section.value === "users") {
      const response = await adminAPI.getUsers();
      users.value = response.data?.data?.items || response.data?.data || [];
    }
  } catch {
    // Keep admin shell usable even if one endpoint is not migrated yet.
  }
}

watch(section, load);
onMounted(load);
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
.stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.stats div,
.row {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}
.stats strong {
  display: block;
  font-size: 34px;
}
.table {
  display: grid;
  gap: 10px;
}
.row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
@media (max-width: 820px) {
  main {
    grid-template-columns: 1fr;
  }
}
</style>
