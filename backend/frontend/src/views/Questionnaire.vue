<template>
  <div class="page">
    <AppHeader />
    <main class="panel">
      <div class="panel-heading">
        <h1>完成职业问卷</h1>
        <p>系统将根据你的职业、兴趣和使用目标推荐更适合的网站资源。</p>
      </div>
      <QuestionnaireForm
        v-if="!loading && tokenValid"
        :occupations="options.occupations"
        :purposes="options.purposes"
        :interests="options.interests"
        :skill-levels="options.skill_levels"
        :preferences="options.preferences"
        :submitting="submitting"
        @submit="submit"
      />
      <LoadingState v-else-if="loading" text="正在加载问卷..." />
      <p v-if="error" class="error">{{ error }}</p>
      <div v-if="!loading" class="secondary-actions">
        <button v-if="tokenValid" type="button" class="ghost" @click="skip">
          暂不填写，返回首页
        </button>
        <button v-else type="button" class="ghost" @click="relogin">
          重新登录
        </button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import QuestionnaireForm from "../components/questionnaire/QuestionnaireForm.vue";
import { questionnaireAPI, unwrapResponse } from "../utils/api";
import { getAccessToken, isValidAuthToken } from "../utils/auth";
import { useUserStore } from "../stores/user";
import { errorToast, successToast } from "../utils/toast";

const router = useRouter();
const userStore = useUserStore();
const error = ref("");
const loading = ref(false);
const submitting = ref(false);
const tokenValid = ref(true);
const options = reactive({
  occupations: [],
  purposes: [],
  interests: [],
  skill_levels: [],
  preferences: [],
});
const fallbackOptions = {
  occupations: [
    "学生",
    "前端开发",
    "后端开发",
    "产品经理",
    "UI/UX 设计师",
    "运营",
    "教师",
    "自媒体创作者",
    "数据分析师",
    "其他",
  ],
  skill_levels: ["入门", "熟练", "进阶", "专业"],
  purposes: [
    "学习提升",
    "编程开发",
    "论文写作",
    "PPT 制作",
    "设计创作",
    "办公效率",
    "产品运营",
    "数据分析",
  ],
  interests: [
    "AI工具",
    "编程开发",
    "设计资源",
    "学习成长",
    "效率办公",
    "产品运营",
    "数据分析",
    "内容创作",
  ],
  preferences: [
    "免费优先",
    "中文网站",
    "国外优质资源",
    "免登录使用",
    "教程丰富",
    "工具类网站",
    "文档类网站",
  ],
};

function isValidJwt(token) {
  return isValidAuthToken(token);
}

function applyFallbackOptions() {
  Object.entries(fallbackOptions).forEach(([key, values]) => {
    if (!Array.isArray(options[key]) || options[key].length === 0) {
      options[key] = values;
    }
  });
}

async function submit(form) {
  if (submitting.value) return;
  const token = getAccessToken();
  if (!isValidJwt(token)) {
    tokenValid.value = false;
    error.value = "登录状态异常，请重新登录";
    errorToast(error.value);
    return;
  }
  if (!form.occupation) {
    error.value = "请选择你的职业";
    errorToast(error.value);
    return;
  }
  if (!form.interests.length) {
    error.value = "请选择至少一个兴趣方向";
    errorToast(error.value);
    return;
  }
  submitting.value = true;
  error.value = "";
  try {
    await questionnaireAPI.submit(form);
    localStorage.setItem("questionnaire_completed", "true");
    successToast("问卷保存成功");
    router.replace("/");
  } catch (err) {
    error.value = err.response?.data?.msg || "问卷保存失败，请稍后重试";
    errorToast(error.value);
  } finally {
    submitting.value = false;
  }
}

function skip() {
  router.push("/");
}

function relogin() {
  userStore.logout();
  router.replace("/login");
}

onMounted(async () => {
  const token = getAccessToken();
  tokenValid.value = isValidJwt(token);
  if (!tokenValid.value) {
    error.value = "登录状态异常，请重新登录";
    applyFallbackOptions();
    return;
  }

  loading.value = true;
  try {
    const response = await questionnaireAPI.get();
    Object.assign(options, unwrapResponse(response) || {});
    applyFallbackOptions();
  } catch (err) {
    error.value = err.response?.data?.msg || "问卷选项加载失败，请稍后重试";
    errorToast(error.value);
    applyFallbackOptions();
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background:
    radial-gradient(
      circle at 12% 18%,
      rgba(191, 245, 237, 0.36),
      transparent 28%
    ),
    radial-gradient(
      circle at 88% 28%,
      rgba(255, 112, 88, 0.16),
      transparent 30%
    ),
    linear-gradient(180deg, #ffffff 0%, #fffaf8 100%);
}

.panel {
  display: grid;
  gap: 30px;
  width: min(980px, calc(100% - 40px));
  margin: 52px auto 78px;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  padding: clamp(24px, 4vw, 42px);
  box-shadow: var(--shadow-card);
}

.panel-heading {
  display: grid;
  gap: 10px;
  text-align: center;
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(34px, 5vw, 52px);
  line-height: 1.12;
}

.panel-heading p {
  max-width: 700px;
  margin: 0 auto;
  color: #718096;
  line-height: 1.7;
}

.error {
  margin: 0;
  color: #b91c1c;
  font-weight: 750;
}

.secondary-actions {
  display: flex;
  justify-content: center;
}

.ghost {
  border: 1px solid rgba(255, 112, 88, 0.34);
  border-radius: var(--radius-pill);
  background: #ffffff;
  color: var(--color-primary);
  padding: 12px 18px;
  font-weight: 850;
}

.ghost:hover,
.ghost:focus-visible {
  background: var(--color-soft-orange);
  color: var(--color-primary-dark);
  outline: none;
}

@media (max-width: 768px) {
  .panel {
    width: min(100% - 28px, 980px);
    margin-top: 32px;
  }
}
</style>
