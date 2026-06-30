<template>
  <AdminLayout>
    <h1>标签管理</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <form class="form-grid" @submit.prevent="saveTag">
      <label>标签名称<input v-model.trim="form.name" required /></label>
      <label
        >标签类型<input v-model.trim="form.type" placeholder="general"
      /></label>
      <div class="actions">
        <button class="primary" type="submit">
          {{ editingId ? "保存标签" : "新增标签" }}
        </button>
        <button v-if="editingId" type="button" @click="resetForm">
          取消编辑
        </button>
      </div>
    </form>
    <LoadingState v-if="loading" text="正在加载标签..." />
    <div v-else-if="tags.length" class="table">
      <div class="row header">
        <span>名称</span><span>类型</span><span>使用次数</span><span>操作</span>
      </div>
      <div v-for="tag in tags" :key="tag.id || tag.name" class="row">
        <span>{{ tag.name }}</span>
        <span>{{ tag.type || "general" }}</span>
        <span>{{ tag.usage_count || tag.count || 0 }}</span>
        <span class="actions">
          <button type="button" @click="editTag(tag)">编辑</button>
          <button class="danger" type="button" @click="deleteTag(tag)">
            删除
          </button>
        </span>
      </div>
    </div>
    <EmptyState
      v-else
      title="暂无标签"
      description="可以新增标签用于网站筛选。"
    />
  </AdminLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import EmptyState from "../../components/common/EmptyState.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";
import { readData } from "./adminHelpers";

const loading = ref(false);
const error = ref("");
const tags = ref([]);
const editingId = ref(null);
const form = reactive({ name: "", type: "general" });

function resetForm() {
  editingId.value = null;
  Object.assign(form, { name: "", type: "general" });
}

function editTag(tag) {
  editingId.value = tag.id;
  Object.assign(form, { name: tag.name || "", type: tag.type || "general" });
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    tags.value = readData(await adminAPI.getTags());
  } catch (err) {
    error.value = err.response?.data?.msg || "标签加载失败";
  } finally {
    loading.value = false;
  }
}

async function saveTag() {
  try {
    if (editingId.value) {
      await adminAPI.updateTag(editingId.value, form);
    } else {
      await adminAPI.createTag(form);
    }
    resetForm();
    await load();
  } catch (err) {
    error.value = err.response?.data?.msg || "标签保存失败";
  }
}

async function deleteTag(tag) {
  await adminAPI.deleteTag(tag.id);
  tags.value = tags.value.filter((item) => item.id !== tag.id);
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";
</style>
