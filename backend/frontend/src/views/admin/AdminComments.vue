<template>
  <AdminShell>
    <h1>Comments</h1>
    <EmptyState
      title="Comments moderation"
      description="Comment moderation endpoint can be connected here."
    />
  </AdminShell>
</template>

<script setup>
import EmptyState from "../../components/common/EmptyState.vue";
import AdminShell from "./AdminShell.vue";
</script>

<style scoped>
h1 {
  margin-top: 0;
}
</style>
