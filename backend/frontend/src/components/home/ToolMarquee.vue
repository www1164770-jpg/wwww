<template>
  <section
    id="tools"
    class="tool-marquee home-anchor-section reveal-on-scroll"
    aria-label="Popular website recommendations"
  >
    <div ref="viewportRef" class="tool-marquee__viewport">
      <div :key="marqueeKey" class="tool-marquee__track">
        <button
          v-for="site in duplicatedSites"
          :key="site.key"
          type="button"
          class="tool-marquee__item"
          @click="visitSite(site)"
        >
          {{ site.name }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  sites: { type: Array, default: () => [] },
});
const emit = defineEmits(["visit"]);

const marqueeKey = ref(0);
const viewportRef = ref(null);

const fallbackSites = [
  { name: "ChatGPT", url: "https://chatgpt.com" },
  { name: "Claude", url: "https://claude.ai" },
  { name: "Gemini", url: "https://gemini.google.com" },
  { name: "Perplexity", url: "https://www.perplexity.ai" },
  { name: "GitHub", url: "https://github.com" },
  { name: "MDN", url: "https://developer.mozilla.org" },
  { name: "Vue", url: "https://vuejs.org" },
  { name: "Figma", url: "https://www.figma.com" },
  { name: "Canva", url: "https://www.canva.com" },
  { name: "Notion", url: "https://www.notion.so" },
  { name: "飞书", url: "https://www.feishu.cn" },
  { name: "ProcessOn", url: "https://www.processon.com" },
].sort(() => Math.random() - 0.5);

const displaySites = computed(() => {
  const sites = props.sites.filter((site) => site?.name);
  if (!sites.length) return fallbackSites;
  if (sites.length >= 8) return sites;

  const used = new Set(sites.map((site) => site.id || site.url || site.name));
  return [
    ...sites,
    ...fallbackSites.filter(
      (site) => !used.has(site.id || site.url || site.name),
    ),
  ].slice(0, 8);
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

function restartMarquee() {
  marqueeKey.value += 1;
  if (viewportRef.value) {
    viewportRef.value.scrollLeft = 0;
  }
}

function handleVisibilityChange() {
  if (!document.hidden) {
    restartMarquee();
  }
}

onMounted(() => {
  window.addEventListener("pageshow", restartMarquee);
  window.addEventListener("focus", restartMarquee);
  document.addEventListener("visibilitychange", handleVisibilityChange);
});

onBeforeUnmount(() => {
  window.removeEventListener("pageshow", restartMarquee);
  window.removeEventListener("focus", restartMarquee);
  document.removeEventListener("visibilitychange", handleVisibilityChange);
});
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
  overscroll-behavior-x: contain;
  scrollbar-width: none;
  touch-action: pan-x;
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
  will-change: transform;
}

.tool-marquee:hover .tool-marquee__track,
.tool-marquee:focus-within .tool-marquee__track {
  animation-play-state: paused;
}

.tool-marquee__item {
  display: inline-grid;
  min-width: auto;
  min-height: 44px;
  place-items: center;
  flex: 0 0 auto;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: #94a3b8;
  padding: 0;
  font-size: clamp(24px, 3vw, 28px);
  font-weight: 800;
  letter-spacing: 0;
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
