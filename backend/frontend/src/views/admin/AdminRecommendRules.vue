<template>
  <AdminLayout>
    <div class="page-head">
      <h1>推荐规则管理</h1>
      <p>配置职业匹配、权重、黑名单和推荐理由文案，供推荐接口迭代使用。</p>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <LoadingState v-if="loading" text="正在加载推荐规则..." />

    <form v-else class="form-grid config-form" @submit.prevent="save">
      <label>
        黑名单网站
        <textarea
          v-model="blacklistText"
          placeholder="多个网站名用逗号或换行分隔"
        ></textarea>
      </label>

      <label>
        推荐权重 JSON
        <textarea
          v-model="weightsText"
          class="json-box"
          spellcheck="false"
        ></textarea>
      </label>

      <label>
        职业匹配规则 JSON
        <textarea
          v-model="occupationWeightsText"
          class="json-box"
          spellcheck="false"
        ></textarea>
      </label>

      <label>
        推荐理由模板 JSON
        <textarea
          v-model="reasonTemplatesText"
          class="json-box"
          spellcheck="false"
        ></textarea>
      </label>

      <div class="actions wide">
        <button class="primary" type="submit" :disabled="saving">
          {{ saving ? "保存中..." : "保存推荐规则" }}
        </button>
      </div>
    </form>
  </AdminLayout>
</template>

<script setup>
import { onMounted, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";
import { errorToast, successToast } from "../../utils/toast";
import { readData } from "./adminHelpers";

const loading = ref(false);
const saving = ref(false);
const error = ref("");
const blacklistText = ref("");
const weightsText = ref("{}");
const occupationWeightsText = ref("{}");
const reasonTemplatesText = ref("{}");

function splitList(value) {
  return String(value || "")
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseJsonField(value, label) {
  try {
    return JSON.parse(value || "{}");
  } catch {
    throw new Error(`${label} 必须是合法 JSON`);
  }
}

function buildPayload() {
  return {
    blacklist: splitList(blacklistText.value),
    weights: parseJsonField(weightsText.value, "推荐权重"),
    occupation_site_weights: parseJsonField(
      occupationWeightsText.value,
      "职业匹配规则",
    ),
    reason_templates: parseJsonField(reasonTemplatesText.value, "推荐理由模板"),
  };
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const data = readData(await adminAPI.getRecommendRules(), {});
    blacklistText.value = (data.blacklist || []).join("，");
    weightsText.value = JSON.stringify(data.weights || {}, null, 2);
    occupationWeightsText.value = JSON.stringify(
      data.occupation_site_weights || {},
      null,
      2,
    );
    reasonTemplatesText.value = JSON.stringify(
      data.reason_templates || {},
      null,
      2,
    );
  } catch (err) {
    error.value = err.response?.data?.msg || "推荐规则加载失败";
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
    await adminAPI.saveRecommendRules(buildPayload());
    successToast("推荐规则已保存");
    await load();
  } catch (err) {
    error.value = err.message || err.response?.data?.msg || "推荐规则保存失败";
    errorToast(error.value);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";

.config-form {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.json-box {
  min-height: 220px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.wide {
  grid-column: 1 / -1;
}
</style>
