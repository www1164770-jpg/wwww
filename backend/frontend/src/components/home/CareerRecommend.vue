<template>
  <section id="career" class="home-section career-section">
    <div class="section-heading">
      <p>职业推荐</p>
      <h2>选择你的职业，快速找到适合的工具组合。</h2>
    </div>

    <div class="career-grid">
      <button
        v-for="career in careerRecommendations"
        :key="career.name"
        type="button"
        class="career-card"
        :class="{ active: activeCareer === career.name }"
        @click="$emit('select-career', career.name)"
      >
        <span class="career-icon">{{ career.icon }}</span>
        <strong>{{ career.name }}</strong>
        <small>{{ career.description }}</small>
        <span class="tag-row">
          <em v-for="tag in career.tags" :key="tag">{{ tag }}</em>
        </span>
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  activeCareer: {
    type: String,
    default: "",
  },
});

defineEmits(["select-career"]);

const careerRecommendations = [
  {
    name: "学生",
    icon: "学",
    description: "论文写作、文献检索、翻译、PPT 制作和在线课程工具。",
    tags: ["论文", "PPT", "翻译"],
  },
  {
    name: "程序员",
    icon: "码",
    description: "AI 编程、代码托管、接口测试、技术文档和部署平台。",
    tags: ["编程", "接口", "部署"],
  },
  {
    name: "设计师",
    icon: "设",
    description: "AI 绘图、素材库、配色、字体、图片压缩和原型设计工具。",
    tags: ["绘图", "素材", "设计"],
  },
  {
    name: "运营",
    icon: "营",
    description: "热点分析、文案生成、排版工具、数据看板和短视频工具。",
    tags: ["文案", "数据", "短视频"],
  },
];
</script>

<style scoped>
.career-section {
  display: grid;
  gap: 24px;
  padding: 46px 0 34px;
}

.career-section {
  border-radius: var(--radius-large);
  background: linear-gradient(180deg, #ffffff 0%, #fff8f6 100%);
}

.career-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.career-card {
  display: grid;
  gap: 13px;
  min-height: 230px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: 20px;
  text-align: left;
  background: #ffffff;
  transition:
    border-color var(--transition),
    transform var(--transition),
    box-shadow var(--transition),
    background var(--transition);
}

.career-card:hover,
.career-card.active {
  border-color: rgba(255, 112, 88, 0.5);
  background: var(--color-soft-orange);
  transform: translateY(-4px);
  box-shadow: var(--shadow-card);
}

.career-icon {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 16px;
  color: #ffffff;
  background: var(--color-primary);
  font-weight: 850;
}

.career-card strong {
  color: var(--color-heading);
  font-size: 18px;
}

.career-card small {
  color: var(--color-text);
  line-height: 1.65;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-row em {
  border-radius: var(--radius-pill);
  padding: 6px 10px;
  color: var(--color-primary-dark);
  background: rgba(255, 112, 88, 0.1);
  font-size: 12px;
  font-style: normal;
  font-weight: 750;
}

@media (max-width: 980px) {
  .career-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .career-grid {
    grid-template-columns: 1fr;
  }
}
</style>
