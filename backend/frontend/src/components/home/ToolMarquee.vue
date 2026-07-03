<template>
  <section
    id="tools"
    class="tool-marquee home-anchor-section"
    aria-label="常用工具品牌"
  >
    <div class="tool-marquee__viewport">
      <div class="tool-marquee__track">
        <span
          v-for="site in duplicatedSites"
          :key="site.key"
          class="tool-marquee__item"
          role="link"
          tabindex="0"
          @click="visitSite(site)"
          @keydown.enter.prevent="visitSite(site)"
          @keydown.space.prevent="visitSite(site)"
        >
          {{ site.name }}
        </span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  sites: { type: Array, default: () => [] },
});
const emit = defineEmits(["visit"]);

const fallbackSites = [
  { name: "ChatGPT", url: "https://chatgpt.com" },
  { name: "Claude", url: "https://claude.ai" },
  { name: "Notion", url: "https://www.notion.so" },
  { name: "Canva", url: "https://www.canva.com" },
  { name: "GitHub", url: "https://github.com" },
  { name: "Figma", url: "https://www.figma.com" },
  { name: "掘金", url: "https://juejin.cn" },
  { name: "知乎", url: "https://www.zhihu.com" },
  { name: "Bilibili", url: "https://www.bilibili.com" },
  { name: "LeetCode", url: "https://leetcode.cn" },
  { name: "MDN", url: "https://developer.mozilla.org" },
  { name: "Vercel", url: "https://vercel.com" },
].sort(() => Math.random() - 0.5);

const displaySites = computed(() => {
  const sites = props.sites.filter((site) => site?.name);
  return sites.length ? sites : fallbackSites;
});

const duplicatedSites = computed(() =>
  [...displaySites.value, ...displaySites.value].map((site, index) => ({
    ...site,
    key: `${site.id || site.url || site.name}-${index}`,
  })),
);

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
.tool-marquee {
  width: 100%;
  overflow: hidden;
  border-top: 1px solid var(--color-border-soft);
  border-bottom: 1px solid var(--color-border-soft);
  background: #ffffff;
}

.tool-marquee__viewport {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  overscroll-behavior-inline: contain;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
}

.tool-marquee__viewport::-webkit-scrollbar {
  display: none;
}

.tool-marquee__track {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: clamp(26px, 4vw, 46px);
  width: max-content;
  min-width: 100%;
  min-height: 96px;
  padding: 0 32px;
  animation: marquee-scroll 34s linear infinite;
}

.tool-marquee:hover .tool-marquee__track,
.tool-marquee:focus-within .tool-marquee__track {
  animation-play-state: paused;
}

.tool-marquee__item {
  flex: 0 0 auto;
  cursor: pointer;
  color: #94a3b8;
  font-size: clamp(24px, 3vw, 28px);
  font-weight: 700;
  white-space: nowrap;
  transition: color var(--transition);
}

.tool-marquee__item:hover,
.tool-marquee__item:focus-visible {
  color: var(--color-heading);
  outline: none;
}

@keyframes marquee-scroll {
  from {
    transform: translateX(0);
  }

  to {
    transform: translateX(-50%);
  }
}

@media (max-width: 768px) {
  .tool-marquee__track {
    animation: none;
    gap: 24px;
    padding: 0 20px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tool-marquee__track {
    animation: none;
  }
}
</style>
