<template>
  <form class="questionnaire-form" @submit.prevent="$emit('submit', form)">
    <section class="question-card">
      <h2>基础画像</h2>
      <div class="select-grid">
        <label>
          职业
          <select v-model="form.occupation" required>
            <option disabled value="">请选择职业</option>
            <option v-for="item in occupations" :key="item" :value="item">
              {{ labelText(item) }}
            </option>
          </select>
        </label>
        <label>
          能力水平
          <select v-model="form.skill_level" required>
            <option disabled value="">请选择能力水平</option>
            <option v-for="item in skillLevels" :key="item" :value="item">
              {{ labelText(item) }}
            </option>
          </select>
        </label>
      </div>
    </section>

    <fieldset class="question-card">
      <legend>使用目的</legend>
      <label v-for="item in purposes" :key="item" class="pill-option">
        <input v-model="form.purposes" type="checkbox" :value="item" />
        <span>{{ labelText(item) }}</span>
      </label>
    </fieldset>
    <fieldset class="question-card">
      <legend>兴趣方向</legend>
      <label v-for="item in interests" :key="item" class="pill-option">
        <input v-model="form.interests" type="checkbox" :value="item" />
        <span>{{ labelText(item) }}</span>
      </label>
    </fieldset>
    <fieldset class="question-card">
      <legend>资源偏好</legend>
      <label v-for="item in preferences" :key="item" class="pill-option">
        <input v-model="form.preferences" type="checkbox" :value="item" />
        <span>{{ labelText(item) }}</span>
      </label>
    </fieldset>
    <div class="submit-bar">
      <button type="submit">保存问卷</button>
    </div>
  </form>
</template>

<script setup>
import { reactive } from "vue";

defineProps({
  occupations: { type: Array, default: () => [] },
  purposes: { type: Array, default: () => [] },
  interests: { type: Array, default: () => [] },
  skillLevels: { type: Array, default: () => [] },
  preferences: { type: Array, default: () => [] },
});
defineEmits(["submit"]);

const form = reactive({
  occupation: "",
  skill_level: "",
  purposes: [],
  interests: [],
  preferences: [],
});

const labelMap = {
  programmer: "程序员",
  designer: "设计师",
  product_manager: "产品经理",
  operations: "运营",
  marketing: "市场营销",
  ecommerce: "电商从业者",
  teacher: "教师",
  student: "学生",
  creator: "内容创作者",
  other: "其他",
  beginner: "入门",
  junior: "初级",
  intermediate: "中级",
  senior: "高级",
  efficiency: "提升效率",
  learning: "学习成长",
  ai_tools: "AI 工具探索",
  project_development: "项目开发",
  design_assets: "设计素材",
  data_analysis: "数据分析",
  content_creation: "内容创作",
  industry_news: "行业资讯",
  "AI tools": "AI 工具",
  programming: "编程开发",
  "design resources": "设计资源",
  "product management": "产品管理",
  growth: "增长运营",
  "data analysis": "数据分析",
  "office efficiency": "办公效率",
  "learning platforms": "学习平台",
  "startup resources": "创业资源",
  assets: "素材资源",
  "free first": "优先免费",
  "professional first": "优先专业",
  "domestic first": "优先国内",
  "international first": "优先国外",
  "tutorial first": "优先教程",
  "efficiency first": "优先效率",
};

function labelText(value) {
  return labelMap[value] || value;
}
</script>

<style scoped>
.questionnaire-form {
  display: grid;
  gap: 18px;
}

.question-card {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 22px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.04);
}

.question-card h2,
legend {
  width: 100%;
  margin: 0;
  color: var(--color-heading);
  font-size: 20px;
  font-weight: 850;
}

fieldset {
  margin: 0;
}

.select-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  width: 100%;
}

label {
  display: grid;
  gap: 8px;
  color: var(--color-heading);
  font-weight: 750;
}

select {
  width: 100%;
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #ffffff;
  padding: 13px 14px;
}

.pill-option {
  display: inline-flex;
  align-items: center;
  gap: 0;
}

.pill-option input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.pill-option span {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: #ffffff;
  color: var(--color-text);
  padding: 10px 15px;
  transition:
    background var(--transition),
    border-color var(--transition),
    color var(--transition),
    transform var(--transition),
    box-shadow var(--transition);
}

.pill-option input:checked + span {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(255, 112, 88, 0.16);
}

.pill-option:hover span,
.pill-option input:focus-visible + span {
  border-color: rgba(255, 112, 88, 0.48);
  transform: translateY(-1px);
}

.submit-bar {
  position: sticky;
  bottom: 18px;
  display: flex;
  justify-content: flex-end;
  border: 1px solid rgba(229, 231, 235, 0.82);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  padding: 12px;
  backdrop-filter: blur(14px);
}

button {
  min-width: 160px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 15px 20px;
  font-weight: 850;
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.18);
}

button:hover,
button:focus-visible {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  outline: none;
}

@media (max-width: 680px) {
  .select-grid {
    grid-template-columns: 1fr;
  }

  .submit-bar,
  button {
    width: 100%;
  }
}
</style>
