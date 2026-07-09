<template>
  <AdminLayout>
    <div class="page-head">
      <h1>问卷管理</h1>
      <p>配置首次登录问卷题目、选项、必填状态，并查看用户问卷统计。</p>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <LoadingState v-if="loading" text="正在加载问卷配置..." />
    <template v-else>
      <div class="stats-row">
        <AdminStatsCard label="画像数量" :value="stats.total_profiles || 0" />
        <AdminStatsCard
          label="完成问卷用户"
          :value="stats.completed_users || 0"
        />
        <AdminStatsCard
          label="职业类型"
          :value="(stats.occupation_distribution || []).length"
        />
      </div>

      <form class="form-grid config-form" @submit.prevent="save">
        <div class="question-list">
          <div
            v-for="(question, index) in questions"
            :key="question.key || index"
            class="question-row"
          >
            <label>
              字段标识
              <input v-model.trim="question.key" required />
            </label>
            <label>
              题目名称
              <input v-model.trim="question.label" required />
            </label>
            <label>
              选项
              <textarea
                v-model="question.optionsText"
                placeholder="多个选项用逗号分隔"
              ></textarea>
            </label>
            <label class="check">
              <input v-model="question.required" type="checkbox" />
              必填
            </label>
            <label class="check">
              <input v-model="question.multiple" type="checkbox" />
              多选
            </label>
            <button
              type="button"
              class="danger"
              :disabled="questions.length <= 1"
              @click="removeQuestion(index)"
            >
              删除
            </button>
          </div>
        </div>

        <label class="wide">
          职业与标签映射 JSON
          <textarea
            v-model="occupationTagMapText"
            class="json-box"
            spellcheck="false"
          ></textarea>
        </label>

        <div class="actions wide">
          <button type="button" @click="addQuestion">新增题目</button>
          <button class="primary" type="submit" :disabled="saving">
            {{ saving ? "保存中..." : "保存问卷配置" }}
          </button>
        </div>
      </form>

      <section class="stats-panel">
        <h2>职业分布</h2>
        <div v-if="(stats.occupation_distribution || []).length">
          <div
            v-for="item in stats.occupation_distribution"
            :key="item.occupation"
            class="rank-row"
          >
            <span>{{ item.occupation || "未填写" }}</span>
            <strong>{{ item.count || 0 }}</strong>
          </div>
        </div>
        <EmptyState
          v-else
          title="暂无问卷统计"
          description="用户提交问卷后，这里会展示职业分布。"
        />
      </section>
    </template>
  </AdminLayout>
</template>

<script setup>
import { onMounted, ref } from "vue";
import AdminLayout from "../../components/admin/AdminLayout.vue";
import AdminStatsCard from "../../components/admin/AdminStatsCard.vue";
import EmptyState from "../../components/common/EmptyState.vue";
import LoadingState from "../../components/common/LoadingState.vue";
import { adminAPI } from "../../utils/api";
import { errorToast, successToast } from "../../utils/toast";
import { readData } from "./adminHelpers";

const loading = ref(false);
const saving = ref(false);
const error = ref("");
const questions = ref([]);
const stats = ref({});
const occupationTagMapText = ref("{}");

function splitOptions(value) {
  return String(value || "")
    .split(/[,，\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeQuestion(question = {}) {
  const options = Array.isArray(question.options) ? question.options : [];
  return {
    key: question.key || "",
    label: question.label || "",
    required: Boolean(question.required),
    multiple: Boolean(question.multiple),
    optionsText: options.join("，"),
  };
}

function buildPayload() {
  let occupationTagMap = {};
  try {
    occupationTagMap = JSON.parse(occupationTagMapText.value || "{}");
  } catch {
    throw new Error("职业与标签映射必须是合法 JSON");
  }
  return {
    questions: questions.value.map((question) => ({
      key: question.key,
      label: question.label,
      required: question.required,
      multiple: question.multiple,
      options: splitOptions(question.optionsText),
    })),
    occupation_tag_map: occupationTagMap,
  };
}

function addQuestion() {
  questions.value.push(
    normalizeQuestion({
      key: "",
      label: "",
      required: true,
      multiple: false,
      options: [],
    }),
  );
}

function removeQuestion(index) {
  questions.value.splice(index, 1);
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const payload = readData(await adminAPI.getQuestionnaires(), {});
    const rawConfig = payload.raw_config || payload.config || {};
    const config = payload.config || rawConfig;
    questions.value = (config.questions || []).map(normalizeQuestion);
    if (!questions.value.length) addQuestion();
    occupationTagMapText.value = JSON.stringify(
      rawConfig.occupation_tag_map || config.occupation_tag_map || {},
      null,
      2,
    );
    stats.value = payload.stats || {};
  } catch (err) {
    error.value = err.response?.data?.msg || "问卷配置加载失败";
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
    await adminAPI.saveQuestionnaireConfig(buildPayload());
    successToast("问卷配置已保存");
    await load();
  } catch (err) {
    error.value = err.message || err.response?.data?.msg || "问卷配置保存失败";
    errorToast(error.value);
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
@import "./adminTable.css";

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.config-form {
  grid-template-columns: 1fr;
}

.question-list {
  display: grid;
  gap: 12px;
}

.question-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  align-items: end;
  gap: 12px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 12px;
}

.check {
  grid-template-columns: auto 1fr;
  align-items: center;
}

.check input {
  width: 18px;
  height: 18px;
}

.wide {
  grid-column: 1 / -1;
}

.json-box {
  min-height: 150px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.stats-panel {
  margin-top: 18px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 16px;
}

.rank-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid #f3f4f6;
  padding: 10px 0;
}
</style>
