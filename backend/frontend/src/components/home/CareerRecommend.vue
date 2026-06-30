<template>
  <section id="career" class="career-section">
    <div class="section-heading">
      <p>AI 职业推荐</p>
      <h2>选择你的身份，快速找到适合的工具组合</h2>
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
        <strong>{{ career.name }} / {{ career.scene }}</strong>
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
    scene: "论文写作",
    icon: "学",
    description: "文献检索、论文润色、翻译、PPT 制作和在线课程工具。",
    tags: ["论文", "PPT", "翻译"],
  },
  {
    name: "程序员",
    scene: "开发学习",
    icon: "码",
    description: "AI 编程、代码托管、接口测试、技术文档和部署平台。",
    tags: ["编程", "接口", "部署"],
  },
  {
    name: "设计师",
    scene: "内容创作",
    icon: "设",
    description: "AI 绘图、素材库、配色、字体、图片压缩和原型设计工具。",
    tags: ["绘图", "素材", "设计"],
  },
  {
    name: "运营",
    scene: "自媒体",
    icon: "营",
    description: "热点分析、文案生成、排版工具、数据看板和短视频工具。",
    tags: ["文案", "数据", "短视频"],
  },
];
</script>

<style scoped>
.career-section {
  padding: 32px min(6vw, 72px);
}

.section-heading p {
  margin: 0 0 8px;
  color: #1769aa;
  font-weight: 700;
}

.section-heading h2 {
  margin: 0 0 22px;
  color: #18212f;
  font-size: 30px;
}

.career-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.career-card {
  display: grid;
  gap: 12px;
  min-height: 220px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  padding: 20px;
  text-align: left;
  background: #fff;
  cursor: pointer;
  transition:
    border-color 0.2s,
    transform 0.2s,
    box-shadow 0.2s;
}

.career-card:hover,
.career-card.active {
  border-color: #1769aa;
  transform: translateY(-3px);
  box-shadow: 0 18px 34px rgba(23, 105, 170, 0.14);
}

.career-icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: #1769aa;
  font-weight: 800;
}

.career-card strong {
  color: #18212f;
  font-size: 18px;
}

.career-card small {
  color: #5a6472;
  line-height: 1.6;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-row em {
  border-radius: 999px;
  padding: 5px 9px;
  color: #1769aa;
  background: #e9f4fc;
  font-style: normal;
  font-size: 12px;
}

@media (max-width: 980px) {
  .career-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .career-section {
    padding-inline: 20px;
  }

  .career-grid {
    grid-template-columns: 1fr;
  }
}
</style>
