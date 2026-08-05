<template>
  <AdminLayout>
    <div class="page-head">
      <h1>后台设置</h1>
      <p>集中管理站点名称、注册入口、审核模式和首页模块开关。</p>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <LoadingState v-if="loading" text="正在加载后台设置..." />

    <form v-else class="form-grid" @submit.prevent="save">
      <label>
        站点名称
        <input v-model.trim="form.site_name" required />
      </label>

      <label>
        审核模式
        <select v-model="form.audit_mode">
          <option value="manual">人工审核</option>
          <option value="auto">自动通过</option>
        </select>
      </label>

      <label>
        评论默认状态
        <select v-model="form.comment_default_status">
          <option value="visible">直接展示</option>
          <option value="pending">待审核</option>
        </select>
      </label>

      <label class="check">
        <input v-model="form.allow_registration" type="checkbox" />
        允许用户注册
      </label>

      <label class="wide">
        首页模块
        <textarea
          v-model="homeSectionsText"
          placeholder="categories,career,recommend,hot,latest,tools"
        ></textarea>
      </label>

      <div class="actions wide">
        <button class="primary" type="submit" :disabled="saving">
          {{ saving ? "保存中..." : "保存设置" }}
        </button>
      </div>
    </form>
  </AdminLayout>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";
import { errorToast, successToast } from "../../utils/toast";
import { readData } from "./adminHelpers";

const loading = ref(false);
const saving = ref(false);
const error = ref("");
const homeSectionsText = ref("");
const form = reactive({
  site_name: "",
  audit_mode: "manual",
  allow_registration: true,
  comment_default_status: "visible",
});

function splitSections(value) {
  return String(value || "")
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const data = readData(await adminAPI.getSettings(), {});
    Object.assign(form, {
      site_name: data.site_name || "知航屿",
      audit_mode: data.audit_mode || "manual",
      allow_registration: data.allow_registration !== false,
      comment_default_status: data.comment_default_status || "visible",
    });
    homeSectionsText.value = (data.home_sections || []).join("，");
  } catch (err) {
    error.value = err.response?.data?.msg || "后台设置加载失败";
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (saving.value) return;
  saving.value = true;
  error.value = "";
  try {
    await adminAPI.saveSettings({
      ...form,
      home_sections: splitSections(homeSectionsText.value),
    });
    successToast("后台设置已保存");
    await load();
  } catch (err) {
    error.value = err.response?.data?.msg || "后台设置保存失败";
    errorToast(error.value);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";

.wide {
  grid-column: 1 / -1;
}

.check {
  grid-template-columns: auto 1fr;
  align-items: center;
}

.check input {
  width: 18px;
  height: 18px;
}
</style>
