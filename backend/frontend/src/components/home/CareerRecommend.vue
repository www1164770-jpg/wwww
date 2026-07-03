<template>
  <section class="home-section career-section">
    <div class="section-heading">
      <p>职业推荐</p>
      <h2>选择你的职业，快速找到适合的工具组合。</h2>
    </div>

    <div class="career-grid">
      <button
        v-for="career in careerRecommendations"
        :key="career.key"
        type="button"
        class="career-card"
        :class="{ active: activeCareer === career.key }"
        @click="selectCareer(career)"
      >
        <span class="career-icon">{{ career.icon }}</span>
        <strong>{{ career.name }}</strong>
        <small>{{ career.description }}</small>
        <span class="tag-row">
          <em v-for="keyword in career.keywords" :key="keyword">
            {{ keyword }}
          </em>
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

const emit = defineEmits(["select-career"]);

const careerRecommendations = [
  {
    key: "student",
    name: "学生",
    icon: "学",
    description: "论文写作、文献检索、翻译、PPT 制作和在线课程工具。",
    keywords: ["学习", "论文写作", "PPT", "编程入门"],
  },
  {
    key: "frontend",
    name: "前端开发",
    icon: "前",
    description: "Vue、React、JavaScript、组件设计和前端工程工具。",
    keywords: ["Vue", "React", "JavaScript", "组件"],
  },
  {
    key: "backend",
    name: "后端开发",
    icon: "后",
    description: "接口调试、数据库、Python、框架文档和代码辅助工具。",
    keywords: ["Python", "Flask", "API", "数据库"],
  },
  {
    key: "product",
    name: "产品经理",
    icon: "产",
    description: "需求分析、产品文档、原型流程和数据洞察工具。",
    keywords: ["需求", "原型", "文档", "流程图"],
  },
  {
    key: "uiux",
    name: "UI/UX 设计师",
    icon: "设",
    description: "界面设计、素材查找、图标管理和创意生成工具。",
    keywords: ["Figma", "UI", "图标", "图片"],
  },
  {
    key: "operations",
    name: "运营",
    icon: "营",
    description: "文案生成、内容运营、增长分析和办公协作工具。",
    keywords: ["文案", "内容", "数据分析", "增长"],
  },
  {
    key: "teacher",
    name: "教师",
    icon: "教",
    description: "课件制作、教学设计、题库整理和学习资源工具。",
    keywords: ["教学", "课件", "PPT", "题库"],
  },
  {
    key: "creator",
    name: "自媒体创作者",
    icon: "创",
    description: "内容创作、视频脚本、图片生成和灵感整理工具。",
    keywords: ["写作", "视频", "图片", "AIGC"],
  },
  {
    key: "data",
    name: "数据分析师",
    icon: "数",
    description: "数据分析、可视化、报表整理和效率提升工具。",
    keywords: ["数据分析", "可视化", "Python", "SQL"],
  },
  {
    key: "other",
    name: "其他",
    icon: "AI",
    description: "学习、工作、创作和办公场景里的通用 AI 工具。",
    keywords: ["AI", "效率", "学习", "办公"],
  },
];

function selectCareer(career) {
  emit("select-career", career);
}
</script>

<style scoped>
.career-section {
  display: grid;
  gap: 28px;
  margin-top: 28px;
  border-radius: var(--radius-large);
  background: linear-gradient(180deg, #ffffff 0%, #fff8f6 100%);
  padding: 54px 34px 42px;
}

.career-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.career-card {
  display: grid;
  gap: 14px;
  min-height: 238px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: 22px;
  text-align: left;
  background: #ffffff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
  transition:
    border-color var(--transition),
    transform var(--transition),
    box-shadow var(--transition),
    background var(--transition);
}

.career-card:hover,
.career-card.active {
  border-color: #ff7058;
  background: #fffaf8;
  transform: translateY(-5px);
  box-shadow: var(--shadow-card);
}

.career-card.active {
  box-shadow: 0 16px 38px rgba(255, 112, 88, 0.18);
}

.career-icon {
  display: grid;
  width: 50px;
  height: 50px;
  place-items: center;
  border-radius: 18px;
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
  .career-section {
    padding-inline: 24px;
  }

  .career-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .career-section {
    padding-inline: 18px;
  }

  .career-grid {
    grid-template-columns: 1fr;
  }
}
</style>
