<template>
  <AdminLayout>
    <div class="page-head">
      <h1>用户管理</h1>
      <p>查看用户账号、问卷状态，并处理禁用或解禁操作。</p>
    </div>
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
          <button
            type="button"
            :disabled="isBusy(user.id)"
            @click="toggleStatus(user)"
          >
            {{
              isBusy(user.id)
                ? "处理中..."
                : user.status === "disabled"
                  ? "解禁"
                  : "禁用"
            }}
          </button>
          <button type="button" @click="toggleQuestionnaire(user)">
            查看问卷
          </button>
        </span>
        <div v-if="expandedUserId === user.id" class="questionnaire-detail">
          <strong>问卷信息</strong>
          <span>职业：{{ labelText(user.questionnaire?.occupation) }}</span>
          <span
            >能力水平：{{ labelText(user.questionnaire?.skill_level) }}</span
          >
          <span>兴趣：{{ listText(user.questionnaire?.interests) }}</span>
          <span>偏好：{{ listText(user.questionnaire?.preferences) }}</span>
          <span>用途：{{ listText(user.questionnaire?.purposes) }}</span>
        </div>
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
import { errorToast, successToast } from "../../utils/toast";
import { readData, toDate } from "./adminHelpers";

const loading = ref(false);
const error = ref("");
const users = ref([]);
const expandedUserId = ref(null);
const busyIds = ref([]);
const labelMap = {
  programmer: "程序员",
  designer: "设计师",
  product_manager: "产品经理",
  operations: "运营",
  marketing: "市场营销",
  ecommerce: "电商从业者",
  teacher: "教师",
  student: "学生",
  creator: "内容创作者",
  other: "其他",
  beginner: "入门",
  junior: "初级",
  intermediate: "中级",
  senior: "高级",
};

function listText(value) {
  return Array.isArray(value) && value.length
    ? value.map((item) => labelText(item)).join("、")
    : "暂无";
}

function labelText(value) {
  return labelMap[value] || value || "未填写";
}

function isBusy(id) {
  return busyIds.value.includes(id);
}

function setBusy(id, busy) {
  busyIds.value = busy
    ? [...busyIds.value, id]
    : busyIds.value.filter((item) => item !== id);
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    users.value = readData(await adminAPI.getUsers());
  } catch (err) {
    error.value = err.response?.data?.msg || "用户加载失败";
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}

async function toggleStatus(user) {
  const nextStatus = user.status === "disabled" ? "active" : "disabled";
  setBusy(user.id, true);
  try {
    await adminAPI.updateUserStatus(user.id, nextStatus);
    await load();
    successToast("保存成功");
  } catch (err) {
    error.value = err.response?.data?.msg || "操作失败，请稍后重试";
    errorToast(error.value);
  } finally {
    setBusy(user.id, false);
  }
}

function toggleQuestionnaire(user) {
  expandedUserId.value = expandedUserId.value === user.id ? null : user.id;
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";

.questionnaire-detail {
  grid-column: 1 / -1;
  display: grid;
  gap: 6px;
  border-radius: 8px;
  background: #f8fafc;
  padding: 12px;
  color: #374151;
}
</style>
