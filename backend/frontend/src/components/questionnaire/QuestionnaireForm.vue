<template>
  <form class="questionnaire-form" @submit.prevent="$emit('submit', form)">
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
    <fieldset>
      <legend>使用目的</legend>
      <label v-for="item in purposes" :key="item">
        <input v-model="form.purposes" type="checkbox" :value="item" />
        {{ labelText(item) }}
      </label>
    </fieldset>
    <fieldset>
      <legend>兴趣方向</legend>
      <label v-for="item in interests" :key="item">
        <input v-model="form.interests" type="checkbox" :value="item" />
        {{ labelText(item) }}
      </label>
    </fieldset>
    <fieldset>
      <legend>偏好</legend>
      <label v-for="item in preferences" :key="item">
        <input v-model="form.preferences" type="checkbox" :value="item" />
        {{ labelText(item) }}
      </label>
    </fieldset>
    <button type="submit">保存问卷</button>
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
label,
fieldset {
  display: grid;
  gap: 8px;
}
fieldset {
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}
legend {
  color: #111827;
  font-weight: 800;
}
select {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 11px;
}
button {
  border: 0;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  padding: 13px;
  font-weight: 800;
}
</style>
