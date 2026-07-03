<template>
  <section class="favorite-band">
    <div class="favorite-stack">
      <div class="favorite-copy">
        <p>常用工具推荐</p>
        <h2>精选高频使用的网站资源</h2>
        <span>
          适合日常学习、工作和创作的高质量工具，优先避开首页其他推荐区已展示的网站。
        </span>
      </div>

      <div v-if="displaySites.length" class="favorite-list">
        <button
          v-for="site in displaySites"
          :key="site.id || site.url || site.name"
          type="button"
          @click="visitSite(site)"
        >
          <strong>{{ site.name }}</strong>
          <small>{{ site.summary || site.description || site.url }}</small>
        </button>
      </div>
      <div v-else class="empty-note">暂无常用工具数据</div>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  sites: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["visit"]);

const fallbackSites = [
  {
    name: "Notion",
    url: "https://www.notion.so",
    summary: "笔记、知识库和项目管理工具。",
  },
  {
    name: "飞书",
    url: "https://www.feishu.cn",
    summary: "团队协作、文档和项目沟通平台。",
  },
  {
    name: "ProcessOn",
    url: "https://www.processon.com",
    summary: "在线流程图和思维导图工具。",
  },
  {
    name: "Figma",
    url: "https://www.figma.com",
    summary: "在线协作设计与原型工具。",
  },
  {
    name: "Canva",
    url: "https://www.canva.com",
    summary: "在线设计与内容创作工具。",
  },
  {
    name: "GitHub",
    url: "https://github.com",
    summary: "代码托管与协作开发平台。",
  },
];

const displaySites = computed(() => {
  const sites = props.sites.filter((site) => site?.name);
  return (sites.length ? sites : fallbackSites).slice(0, 6);
});

function normalizeUrl(url) {
  if (!url) return "";
  if (/^https?:\/\//i.test(url)) return url;
  return `https://${url}`;
}

function visitSite(site) {
  emit("visit", { ...site, url: normalizeUrl(site.url) });
}
</script>

<style scoped>
.favorite-band {
  margin-top: 54px;
  background:
    radial-gradient(
      circle at 12% 20%,
      rgba(255, 112, 88, 0.12),
      transparent 28%
    ),
    linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  padding: 96px 0;
}

.favorite-stack {
  display: grid;
  grid-template-columns: minmax(240px, 370px) 1fr;
  gap: 42px;
  width: min(1200px, calc(100% - 40px));
  margin: 0 auto;
}

.favorite-copy p {
  margin: 0 0 10px;
  color: var(--color-primary);
  font-weight: 850;
}

h2 {
  margin: 0 0 14px;
  color: var(--color-heading);
  font-size: clamp(32px, 4vw, 46px);
  line-height: 1.14;
}

.favorite-copy span {
  color: var(--color-text);
  line-height: 1.75;
}

.favorite-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

button,
.empty-note {
  display: grid;
  gap: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: 20px;
  color: var(--color-heading);
  text-align: left;
  background: #ffffff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
}

button {
  transition:
    transform var(--transition),
    box-shadow var(--transition),
    border-color var(--transition);
}

button:hover,
button:focus-visible {
  border-color: rgba(255, 112, 88, 0.34);
  transform: translateY(-4px);
  outline: none;
  box-shadow: var(--shadow-card);
}

small {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-muted);
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.empty-note {
  color: var(--color-muted);
}

@media (max-width: 820px) {
  .favorite-stack {
    grid-template-columns: 1fr;
  }

  .favorite-list {
    grid-template-columns: 1fr;
  }
}
</style>
