<template>
  <AdminLayout>
    <h1>分类管理</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <form class="form-grid" @submit.prevent="saveCategory">
      <label>分类名称<input v-model.trim="form.name" required /></label>
      <label
        >父级分类
        <select v-model="form.parent_id">
          <option value="">一级分类</option>
          <option
            v-for="category in rootCategories"
            :key="category.id"
            :value="category.id"
          >
            {{ category.name }}
          </option>
        </select>
      </label>
      <label
        >图标<input v-model.trim="form.icon" placeholder="图标文本或地址"
      /></label>
      <label
        >排序<input v-model.number="form.sort_order" type="number"
      /></label>
      <label
        >状态
        <select v-model="form.status">
          <option value="active">启用</option>
          <option value="disabled">禁用</option>
        </select>
      </label>
      <div class="actions">
        <button class="primary" type="submit">
          {{ editingId ? "保存分类" : "新增分类" }}
        </button>
        <button v-if="editingId" type="button" @click="resetForm">
          取消编辑
        </button>
      </div>
    </form>
    <LoadingState v-if="loading" text="正在加载分类..." />
    <div v-else-if="categories.length" class="table">
      <div class="row header">
        <span>名称</span><span>父级</span><span>图标</span><span>排序</span
        ><span>状态</span><span>操作</span>
      </div>
      <div v-for="category in categories" :key="category.id" class="row">
        <span>{{ category.name }}</span>
        <span>{{ parentName(category.parent_id) }}</span>
        <span>{{ category.icon || "-" }}</span>
        <span>{{ category.sort_order || 0 }}</span>
        <span>{{ category.status === "disabled" ? "禁用" : "启用" }}</span>
        <span class="actions">
          <button type="button" @click="editCategory(category)">编辑</button>
          <button
            class="danger"
            type="button"
            @click="deleteCategory(category)"
          >
            删除
          </button>
        </span>
      </div>
    </div>
    <EmptyState
      v-else
      title="暂无分类"
      description="可以新增一级或二级分类。"
    />
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import EmptyState from "../../components/common/EmptyState.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";
import { readData } from "./adminHelpers";

const loading = ref(false);
const error = ref("");
const categories = ref([]);
const editingId = ref(null);
const form = reactive({
  name: "",
  parent_id: "",
  icon: "",
  sort_order: 0,
  status: "active",
});
const rootCategories = computed(() =>
  categories.value.filter(
    (item) => !item.parent_id || item.id === editingId.value,
  ),
);

function parentName(parentId) {
  if (!parentId) return "一级分类";
  return categories.value.find((item) => item.id === parentId)?.name || "-";
}

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    name: "",
    parent_id: "",
    icon: "",
    sort_order: 0,
    status: "active",
  });
}

function editCategory(category) {
  editingId.value = category.id;
  Object.assign(form, {
    name: category.name || "",
    parent_id: category.parent_id || "",
    icon: category.icon || "",
    sort_order: category.sort_order || 0,
    status: category.status || "active",
  });
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    categories.value = readData(await adminAPI.getCategories());
  } catch (err) {
    error.value = err.response?.data?.msg || "分类加载失败";
  } finally {
    loading.value = false;
  }
}

async function saveCategory() {
  const payload = { ...form, parent_id: form.parent_id || null };
  try {
    if (editingId.value) {
      await adminAPI.updateCategory(editingId.value, payload);
    } else {
      await adminAPI.createCategory(payload);
    }
    resetForm();
    await load();
  } catch (err) {
    error.value = err.response?.data?.msg || "分类保存失败";
  }
}

async function deleteCategory(category) {
  await adminAPI.deleteCategory(category.id);
  categories.value = categories.value.filter((item) => item.id !== category.id);
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";
</style>
