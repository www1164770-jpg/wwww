<template>
  <AdminLayout>
    <h1>网站管理</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <form class="form-grid" @submit.prevent="saveSite">
      <label>网站名称<input v-model.trim="form.name" required /></label>
      <label>URL<input v-model.trim="form.url" required /></label>
      <label>Logo<input v-model.trim="form.logo_url" /></label>
      <label
        >分类
        <select v-model="form.category_id">
          <option value="">请选择分类</option>
          <option
            v-for="category in categories"
            :key="category.id"
            :value="category.id"
          >
            {{ category.name }}
          </option>
        </select>
      </label>
      <label
        >标签<input
          v-model.trim="form.tagsText"
          placeholder="多个标签用逗号分隔"
      /></label>
      <label
        >适用职业<input
          v-model.trim="form.occupationsText"
          placeholder="多个职业用逗号分隔"
      /></label>
      <label
        >是否免费
        <select v-model="form.is_free">
          <option :value="1">免费</option>
          <option :value="0">付费</option>
        </select>
      </label>
      <label
        >是否需要登录
        <select v-model="form.need_login">
          <option :value="0">不需要</option>
          <option :value="1">需要</option>
        </select>
      </label>
      <label
        >地区
        <select v-model="form.region">
          <option value="domestic">国内</option>
          <option value="international">国外</option>
        </select>
      </label>
      <label
        >推荐等级<input
          v-model.number="form.recommend_level"
          type="number"
          min="0"
      /></label>
      <label
        >状态
        <select v-model="form.status">
          <option value="approved">已通过</option>
          <option value="pending">待审核</option>
          <option value="disabled">已禁用</option>
        </select>
      </label>
      <label>简介<textarea v-model.trim="form.summary"></textarea></label>
      <div class="actions">
        <button class="primary" type="submit">
          {{ editingId ? "保存修改" : "新增网站" }}
        </button>
        <button v-if="editingId" type="button" @click="resetForm">
          取消编辑
        </button>
      </div>
    </form>
    <LoadingState v-if="loading" text="正在加载网站..." />
    <div v-else-if="sites.length" class="table">
      <div class="row header">
        <span>名称</span><span>URL</span><span>分类</span><span>推荐等级</span
        ><span>点击</span><span>收藏</span><span>状态</span><span>操作</span>
      </div>
      <div v-for="site in sites" :key="site.id" class="row">
        <span>{{ site.name }}</span>
        <a :href="site.url" target="_blank" rel="noreferrer">访问</a>
        <span>{{ site.category_name || site.category_id || "-" }}</span>
        <span>{{ site.recommend_level || 0 }}</span>
        <span>{{ site.click_count || site.clicks || 0 }}</span>
        <span>{{ site.favorite_count || 0 }}</span>
        <span>{{ site.status || "approved" }}</span>
        <span class="actions">
          <button type="button" @click="editSite(site)">编辑</button>
          <button class="danger" type="button" @click="deleteSite(site)">
            删除
          </button>
        </span>
      </div>
    </div>
    <EmptyState
      v-else
      title="暂无网站"
      description="可以通过上方表单新增网站。"
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
const sites = ref([]);
const categories = ref([]);
const editingId = ref(null);
const form = reactive({
  name: "",
  url: "",
  logo_url: "",
  category_id: "",
  tagsText: "",
  occupationsText: "",
  is_free: 1,
  need_login: 0,
  region: "domestic",
  recommend_level: 0,
  status: "approved",
  summary: "",
});

function splitText(value) {
  return String(value || "")
    .split(/[,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildPayload() {
  return {
    ...form,
    tags: splitText(form.tagsText),
    occupations: splitText(form.occupationsText),
    category_id: form.category_id || null,
  };
}

function resetForm() {
  editingId.value = null;
  Object.assign(form, {
    name: "",
    url: "",
    logo_url: "",
    category_id: "",
    tagsText: "",
    occupationsText: "",
    is_free: 1,
    need_login: 0,
    region: "domestic",
    recommend_level: 0,
    status: "approved",
    summary: "",
  });
}

function editSite(site) {
  editingId.value = site.id;
  Object.assign(form, {
    name: site.name || "",
    url: site.url || "",
    logo_url: site.logo_url || "",
    category_id: site.category_id || "",
    tagsText: (site.tags || []).join("，"),
    occupationsText: (site.occupations || []).join("，"),
    is_free: site.is_free ? 1 : 0,
    need_login: site.need_login ? 1 : 0,
    region: site.region || "domestic",
    recommend_level: site.recommend_level || 0,
    status: site.status || "approved",
    summary: site.summary || "",
  });
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [siteRes, categoryRes] = await Promise.all([
      adminAPI.getSites({ per_page: 100 }),
      adminAPI.getCategories(),
    ]);
    sites.value = readData(siteRes);
    categories.value = readData(categoryRes);
  } catch (err) {
    error.value = err.response?.data?.msg || "网站列表加载失败";
  } finally {
    loading.value = false;
  }
}

async function saveSite() {
  try {
    if (editingId.value) {
      await adminAPI.updateSite(editingId.value, buildPayload());
    } else {
      await adminAPI.createSite(buildPayload());
    }
    resetForm();
    await load();
  } catch (err) {
    error.value = err.response?.data?.msg || "网站保存失败";
  }
}

async function deleteSite(site) {
  await adminAPI.deleteSite(site.id);
  sites.value = sites.value.filter((item) => item.id !== site.id);
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";
</style>
