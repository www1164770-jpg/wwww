<template>
  <AdminLayout>
    <div class="page-head">
      <h1>标签管理</h1>
      <p>维护网站标签，用于筛选、详情展示和相似推荐。</p>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <form class="form-grid" @submit.prevent="saveTag">
      <label>标签名称<input v-model.trim="form.name" required /></label>
      <label
        >标签类型<input v-model.trim="form.type" placeholder="general"
      /></label>
      <div class="actions">
        <button class="primary" type="submit" :disabled="saving">
          {{ saving ? "处理中..." : editingId ? "保存标签" : "新增标签" }}
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
          <button
            type="button"
            :disabled="isBusy(tag.id)"
            @click="editTag(tag)"
          >
            编辑
          </button>
          <button
            class="danger"
            type="button"
            :disabled="isBusy(tag.id)"
            @click="deleteTag(tag)"
          >
            {{ isBusy(tag.id) ? "处理中..." : "删除" }}
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
import { errorToast, successToast } from "../../utils/toast";
import { readData } from "./adminHelpers";

const loading = ref(false);
const error = ref("");
const tags = ref([]);
const editingId = ref(null);
const saving = ref(false);
const busyIds = ref([]);
const form = reactive({ name: "", type: "general" });

function isBusy(id) {
  return busyIds.value.includes(id);
}

function setBusy(id, busy) {
  busyIds.value = busy
    ? [...busyIds.value, id]
    : busyIds.value.filter((item) => item !== id);
}

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
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}

async function saveTag() {
  if (saving.value) return;
  if (!form.name.trim()) {
    error.value = "标签名称不能为空";
    errorToast(error.value);
    return;
  }
  saving.value = true;
  error.value = "";
  try {
    if (editingId.value) {
      await adminAPI.updateTag(editingId.value, form);
    } else {
      await adminAPI.createTag(form);
    }
    resetForm();
    await load();
    successToast("保存成功");
  } catch (err) {
    error.value = err.response?.data?.msg || "标签保存失败";
    errorToast(error.value);
  } finally {
    saving.value = false;
  }
}

async function deleteTag(tag) {
  if (!window.confirm(`确认删除「${tag.name || "该标签"}」吗？`)) return;
  setBusy(tag.id, true);
  try {
    await adminAPI.deleteTag(tag.id);
    tags.value = tags.value.filter((item) => item.id !== tag.id);
    successToast("删除成功");
  } catch (err) {
    error.value = err.response?.data?.msg || "删除失败";
    errorToast(error.value);
  } finally {
    setBusy(tag.id, false);
  }
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";
</style>
