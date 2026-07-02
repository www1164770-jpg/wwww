<template>
  <AdminLayout>
    <div class="page-head">
      <h1>评论审核</h1>
      <p>审核用户提交的评论，处理通过、驳回、标违和删除。</p>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <LoadingState v-if="loading" text="正在加载评论..." />
    <div v-else-if="comments.length" class="table">
      <div class="row header">
        <span>评论内容</span><span>用户</span><span>网站</span><span>评分</span
        ><span>状态</span><span>提交时间</span><span>操作</span>
      </div>
      <div v-for="comment in comments" :key="comment.id" class="row">
        <span>{{ comment.content }}</span>
        <span>{{ comment.username || comment.user || "-" }}</span>
        <span>{{ comment.site_name || comment.website || "-" }}</span>
        <span>{{ comment.rating || 0 }}</span>
        <span>{{ statusText(comment.status) }}</span>
        <span>{{ toDate(comment.created_at) }}</span>
        <span class="actions">
          <button
            type="button"
            :disabled="isBusy(comment.id)"
            @click="review(comment, 'approve')"
          >
            {{ isBusy(comment.id) ? "处理中..." : "通过" }}
          </button>
          <button
            type="button"
            :disabled="isBusy(comment.id)"
            @click="review(comment, 'reject')"
          >
            驳回
          </button>
          <button
            type="button"
            :disabled="isBusy(comment.id)"
            @click="review(comment, 'violation')"
          >
            标违
          </button>
          <button
            class="danger"
            type="button"
            :disabled="isBusy(comment.id)"
            @click="review(comment, 'delete')"
          >
            {{ isBusy(comment.id) ? "处理中..." : "删除" }}
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
import { errorToast, successToast } from "../../utils/toast";
import { readData, toDate } from "./adminHelpers";

const loading = ref(false);
const error = ref("");
const comments = ref([]);
const busyIds = ref([]);

function isBusy(id) {
  return busyIds.value.includes(id);
}

function setBusy(id, busy) {
  busyIds.value = busy
    ? [...busyIds.value, id]
    : busyIds.value.filter((item) => item !== id);
}

function statusText(status) {
  return (
    {
      visible: "已通过",
      approved: "已通过",
      rejected: "已驳回",
      deleted: "已删除",
      violation: "已标违",
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
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}

async function review(comment, action) {
  if (action === "delete" && !window.confirm("确认删除这条评论吗？")) return;
  setBusy(comment.id, true);
  try {
    await adminAPI.reviewComment(comment.id, action);
    if (action === "delete") {
      comments.value = comments.value.filter((item) => item.id !== comment.id);
      successToast("删除成功");
      return;
    }
    comment.status =
      {
        approve: "visible",
        reject: "rejected",
        violation: "violation",
      }[action] || "rejected";
    successToast("保存成功");
  } catch (err) {
    error.value = err.response?.data?.msg || "操作失败，请稍后重试";
    errorToast(error.value);
  } finally {
    setBusy(comment.id, false);
  }
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";
</style>
