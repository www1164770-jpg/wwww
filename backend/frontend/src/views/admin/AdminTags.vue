<template>
  <AdminShell>
    <h1>Tags</h1>
    <LoadingState v-if="loading" title="Loading tags" />
    <div v-else-if="tags.length" class="table">
      <div v-for="tag in tags" :key="tag.id || tag.name" class="row">
        <span>{{ tag.name }}</span>
        <small>{{ tag.type || "general" }}</small>
      </div>
    </div>
    <EmptyState v-else title="No tags" description="No tags were found." />
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
const tags = ref([]);

onMounted(async () => {
  loading.value = true;
  try {
    const response = await adminAPI.getTags();
    tags.value = readData(response);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
@import "./adminTable.css";
</style>
