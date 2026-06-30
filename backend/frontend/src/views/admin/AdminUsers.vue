<template>
  <AdminShell>
    <h1>Users</h1>
    <LoadingState v-if="loading" title="Loading users" />
    <div v-else-if="users.length" class="table">
      <div v-for="user in users" :key="user.id" class="row">
        <span>{{ user.username || user.email }}</span>
        <small>{{ user.role || user.status || "user" }}</small>
      </div>
    </div>
    <EmptyState v-else title="No users" description="No users were found." />
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
const users = ref([]);

onMounted(async () => {
  loading.value = true;
  try {
    const response = await adminAPI.getUsers();
    users.value = readData(response);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
@import "./adminTable.css";
</style>
