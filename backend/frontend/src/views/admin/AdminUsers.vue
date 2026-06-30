<template>
  <AdminLayout>
    <h1>用户管理</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <LoadingState v-if="loading" text="正在加载用户..." />
    <div v-else-if="users.length" class="table">
      <div class="row header">
        <span>用户名</span><span>邮箱</span><span>角色</span
        ><span>问卷状态</span><span>账号状态</span><span>注册时间</span
        ><span>操作</span>
      </div>
      <div v-for="user in users" :key="user.id" class="row">
        <span>{{ user.username || "-" }}</span>
        <span>{{ user.email || "-" }}</span>
        <span>{{ user.role || "user" }}</span>
        <span>{{ user.questionnaire_completed ? "已完成" : "未完成" }}</span>
        <span>{{ user.status === "disabled" ? "已禁用" : "正常" }}</span>
        <span>{{ toDate(user.created_at) }}</span>
        <span>
          <button type="button" @click="toggleStatus(user)">
            {{ user.status === "disabled" ? "解禁" : "禁用" }}
          </button>
        </span>
      </div>
    </div>
    <EmptyState v-else title="暂无用户" description="当前没有用户数据。" />
  </AdminLayout>
</template>

<script setup>
import { onMounted, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import EmptyState from "../../components/common/EmptyState.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";
import { readData, toDate } from "./adminHelpers";

const loading = ref(false);
const error = ref("");
const users = ref([]);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    users.value = readData(await adminAPI.getUsers());
  } catch (err) {
    error.value = err.response?.data?.msg || "用户加载失败";
  } finally {
    loading.value = false;
  }
}

async function toggleStatus(user) {
  const nextStatus = user.status === "disabled" ? "active" : "disabled";
  await adminAPI.updateUserStatus(user.id, nextStatus);
  user.status = nextStatus;
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";
</style>
