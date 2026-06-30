<template>
  <AdminLayout>
    <h1>评论审核</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <LoadingState v-if="loading" text="正在加载评论..." />
    <div v-else-if="comments.length" class="table">
      <div class="row header">
        <span>评论内容</span><span>用户</span><span>网站</span><span>评分</span
        ><span>状态</span><span>操作</span>
      </div>
      <div v-for="comment in comments" :key="comment.id" class="row">
        <span>{{ comment.content }}</span>
        <span>{{ comment.username || comment.user || "-" }}</span>
        <span>{{ comment.site_name || comment.website || "-" }}</span>
        <span>{{ comment.rating || 0 }}</span>
        <span>{{ statusText(comment.status) }}</span>
        <span class="actions">
          <button type="button" @click="review(comment, 'approve')">
            通过
          </button>
          <button type="button" @click="review(comment, 'reject')">驳回</button>
          <button
            class="danger"
            type="button"
            @click="review(comment, 'delete')"
          >
            删除
          </button>
        </span>
      </div>
    </div>
    <EmptyState v-else title="暂无评论" description="当前没有待处理评论。" />
  </AdminLayout>
</template>

<script setup>
import { onMounted, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import EmptyState from "../../components/common/EmptyState.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";
import { readData } from "./adminHelpers";

const loading = ref(false);
const error = ref("");
const comments = ref([]);

function statusText(status) {
  return (
    {
      visible: "已通过",
      approved: "已通过",
      rejected: "已驳回",
      deleted: "已删除",
      pending: "待审核",
    }[status] ||
    status ||
    "待审核"
  );
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    comments.value = readData(await adminAPI.getComments());
  } catch (err) {
    error.value = err.response?.data?.msg || "评论加载失败";
  } finally {
    loading.value = false;
  }
}

async function review(comment, action) {
  await adminAPI.reviewComment(comment.id, action);
  if (action === "delete") {
    comments.value = comments.value.filter((item) => item.id !== comment.id);
    return;
  }
  comment.status = action === "approve" ? "visible" : "rejected";
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";
</style>
