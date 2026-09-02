<template>
  <section
    class="brand-marquee home-anchor-section reveal-child reveal-description"
    style="--reveal-delay: 520ms"
    aria-label="热门工具与平台"
  >
    <div class="brand-marquee__viewport">
      <div class="brand-marquee__track">
        <div class="brand-marquee__group">
          <a
            v-for="site in displaySites"
            :key="site.key"
            class="brand-marquee__item"
            :href="site.href"
            target="_blank"
            rel="noopener noreferrer"
            :aria-label="`访问 ${displayName(site)}`"
            @click="recordVisit(site, $event)"
            @auxclick.middle="recordVisit(site, $event)"
          >
            <SiteLogo
              class="brand-marquee__logo"
              :name="displayName(site)"
              :url="site.href"
              :logo="resolveSiteLogo(site)"
              size="sm"
              decorative
            />
            <span class="brand-marquee__name">{{ displayName(site) }}</span>
          </a>
        </div>

        <div class="brand-marquee__group" aria-hidden="true">
          <a
            v-for="site in displaySites"
            :key="`${site.key}-clone`"
            class="brand-marquee__item"
            :href="site.href"
            target="_blank"
            rel="noopener noreferrer"
            tabindex="-1"
            @click="recordVisit(site, $event)"
            @auxclick.middle="recordVisit(site, $event)"
          >
            <SiteLogo
              class="brand-marquee__logo"
              :name="displayName(site)"
              :url="site.href"
              :logo="resolveSiteLogo(site)"
              size="sm"
              decorative
            />
            <span class="brand-marquee__name">{{ displayName(site) }}</span>
          </a>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import SiteLogo from "../site/SiteLogo.vue";
import {
  normalizeSiteName,
  normalizeUrl,
  resolveSiteLogo,
} from "../../utils/api";
import { visitSite } from "../../utils/siteVisit";

const props = defineProps({
  sites: { type: Array, default: () => [] },
});

const BRAND_DISPLAY_NAME_MAP = Object.freeze({
  "mdn web docs": "MDN",
  "mdn 官方文档": "MDN",
  "vue.js": "Vue",
  "vue 官方文档": "Vue",
  "flask 官方文档": "Flask",
});

const displaySites = computed(() =>
  props.sites
    .filter((site) => site?.name && normalizeUrl(site.url))
    .map((site) => ({
      ...site,
      href: normalizeUrl(site.url),
      key: site.id || site.url || site.name,
    })),
);

function displayName(site) {
  const explicitName = [
    site?.short_name,
    site?.brand_name,
    site?.display_name,
  ].find((value) => typeof value === "string" && value.trim());
  if (explicitName) return explicitName.trim();

  return (
    BRAND_DISPLAY_NAME_MAP[normalizeSiteName(site?.name)] ||
    site?.name ||
    "网站"
  );
}

function recordVisit(site, event) {
  visitSite({ ...site, url: site.href }, { source: "home_tool", event });
}
</script>

<style scoped>
.brand-marquee {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-top: 1px solid var(--app-border);
  border-bottom: 1px solid var(--app-border);
  background: transparent;
}

.brand-marquee__viewport {
  position: relative;
  overflow: hidden;
  padding: 24px 0;
}

.brand-marquee__viewport::before,
.brand-marquee__viewport::after {
  position: absolute;
  z-index: 2;
  top: 0;
  bottom: 0;
  width: clamp(40px, 8vw, 140px);
  content: "";
  pointer-events: none;
}

.brand-marquee__viewport::before {
  left: 0;
  background: linear-gradient(to right, var(--app-overlay), transparent);
}

.brand-marquee__viewport::after {
  right: 0;
  background: linear-gradient(to left, var(--app-overlay), transparent);
}

.brand-marquee__track {
  display: flex;
  width: max-content;
  align-items: center;
  animation: brand-marquee-scroll 34s linear infinite;
  will-change: transform;
}

.brand-marquee:hover .brand-marquee__track,
.brand-marquee:focus-within .brand-marquee__track {
  animation-play-state: paused;
}

.brand-marquee__group {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: clamp(28px, 4vw, 58px);
  padding-right: clamp(28px, 4vw, 58px);
}

.brand-marquee__item {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 10px;
  color: var(--app-text-secondary);
  font-size: 16px;
  font-weight: 700;
  line-height: 1;
  text-decoration: none;
  white-space: nowrap;
  transition:
    color 180ms ease,
    opacity 180ms ease,
    transform 180ms ease;
}

.brand-marquee__item:hover {
  color: var(--app-text-primary);
  transform: translateY(-2px);
}

.brand-marquee__item:focus-visible {
  border-radius: 10px;
  color: var(--app-text-primary);
  outline: 3px solid rgba(255, 112, 88, 0.28);
  outline-offset: 5px;
  transform: translateY(-2px);
}

:deep(.brand-marquee__logo.site-logo--image) {
  filter: grayscale(1);
  opacity: 0.55;
  transition:
    filter 180ms ease,
    opacity 180ms ease,
    transform 180ms ease;
}

.brand-marquee__item:hover :deep(.brand-marquee__logo.site-logo--image),
.brand-marquee__item:focus-visible
  :deep(.brand-marquee__logo.site-logo--image) {
  filter: grayscale(0);
  opacity: 1;
  transform: scale(1.06);
}

@keyframes brand-marquee-scroll {
  from {
    transform: translateX(0);
  }

  to {
    transform: translateX(-50%);
  }
}

@media (max-width: 640px) {
  .brand-marquee__viewport {
    padding: 18px 0;
  }

  .brand-marquee__group {
    gap: 28px;
    padding-right: 28px;
  }

  .brand-marquee__item {
    gap: 8px;
    font-size: 14px;
  }

  :deep(.brand-marquee__logo.site-logo) {
    width: 25px;
    height: 25px;
  }

  .brand-marquee__viewport::before,
  .brand-marquee__viewport::after {
    width: 36px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .brand-marquee__viewport {
    overflow-x: auto;
    scrollbar-width: thin;
  }

  .brand-marquee__track {
    animation: none;
    will-change: auto;
  }

  .brand-marquee__group[aria-hidden="true"] {
    display: none;
  }
}
</style>
