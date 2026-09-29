<template>
  <img
    v-if="imageSrc && !imageFailed"
    class="site-logo site-logo--image"
    :class="[
      `site-logo--${size}`,
      { 'site-logo--tight': logoScale > 1 },
      { 'site-logo--pending': !imageLoaded },
    ]"
    :src="imageSrc"
    :style="{ transform: `scale(${logoScale})` }"
    :alt="decorative ? '' : `${label} Logo`"
    :width="pixelSize"
    :height="pixelSize"
    loading="lazy"
    decoding="async"
    @load="handleImageLoad"
    @error="handleImageError"
  />
  <span
    v-else
    class="site-logo site-logo--fallback"
    :class="`site-logo--${size}`"
    aria-hidden="true"
  >
    {{ initial }}
  </span>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { getDomain, resolveSiteLogo } from "../../utils/api";
import vueLogo from "../../assets/vue.svg";

const SIMPLE_ICON_CDN = "https://cdn.simpleicons.org";

const BRAND_LOGOS = Object.freeze({
  "cn.vuejs.org": { src: vueLogo, scale: 1.12 },
  "vuejs.org": { src: vueLogo, scale: 1.12 },
  "claude.ai": { slug: "claude", scale: 1.1 },
  "processon.com": { slug: "processon", scale: 1.1 },
  "bilibili.com": { slug: "bilibili", scale: 1.1 },
  "gemini.google.com": { slug: "googlegemini", scale: 1.08 },
  "developer.mozilla.org": { slug: "mdnwebdocs", scale: 1.08 },
  "kaggle.com": { slug: "kaggle", scale: 1.12 },
  "dribbble.com": { slug: "dribbble", scale: 1.12 },
  "github.com": { slug: "github", scale: 1.14 },
  "stackoverflow.com": { slug: "stackoverflow", scale: 1.1 },
  "notion.com": { slug: "notion", scale: 1.1 },
  "figma.com": { slug: "figma", scale: 1.1 },
  "canva.com": { slug: "canva", scale: 1.14 },
  "scholar.google.com": { slug: "googlescholar", scale: 1.1 },
  "redis.io": { slug: "redis", scale: 1.1 },
  "linux.cn": { slug: "linux", scale: 1.08 },
  "rocket.chat": { slug: "rocketdotchat", scale: 1.1 },
  "hackerrank.com": { slug: "hackerrank", scale: 1.1 },
  "clickup.com": { slug: "clickup", scale: 1.1 },
  "home-assistant.io": { slug: "homeassistant", scale: 1.08 },
  "baidu.com": { slug: "baidu", scale: 1.08 },
  "google.com": { slug: "google", scale: 1.08 },
  "wikipedia.org": { slug: "wikipedia", scale: 1.08 },
  "zhihu.com": { slug: "zhihu", scale: 1.08 },
  "douban.com": { slug: "douban", scale: 1.08 },
  "weread.qq.com": { slug: "weread", scale: 1.08 },
  "duckduckgo.com": { slug: "duckduckgo", scale: 1.08 },
  "startpage.com": { slug: "startpage", scale: 1.08 },
});

const LOW_QUALITY_FAVICON_DOMAINS = new Set(["36kr.com"]);

const props = defineProps({
  name: { type: String, default: "" },
  url: { type: String, default: "" },
  logo: { type: String, default: "" },
  scale: { type: Number, default: null },
  size: {
    type: String,
    default: "md",
    validator: (value) => ["sm", "md", "lg"].includes(value),
  },
  decorative: { type: Boolean, default: false },
});

const imageFailed = ref(false);
const imageLoaded = ref(false);
const sourceIndex = ref(0);
const label = computed(() => props.name.trim() || "网站");
const brandLogo = computed(() => {
  const domain = getDomain(props.url).replace(/^www\./, "");
  const matchedDomain = Object.keys(BRAND_LOGOS).find(
    (knownDomain) =>
      domain === knownDomain || domain.endsWith(`.${knownDomain}`),
  );
  const definition = matchedDomain ? BRAND_LOGOS[matchedDomain] : null;
  if (!definition) return null;

  return {
    src:
      definition.src ||
      `${SIMPLE_ICON_CDN}/${definition.slug}?viewbox=auto`,
    scale: definition.scale || 1,
    isLocal: Boolean(definition.src),
  };
});

function isFavicon(source) {
  return /google\.com\/s2\/favicons|icons\.duckduckgo\.com\/ip3|\.ico(?:[?#]|$)/i.test(
    source,
  );
}

function isSvgSource(source) {
  return (
    /\.svg(?:[?#]|$)/i.test(source) ||
    source.startsWith(SIMPLE_ICON_CDN)
  );
}

const logoSources = computed(() => {
  const domain = getDomain(props.url);
  const providedLogo = String(props.logo || "").trim();
  const skipFaviconSources = LOW_QUALITY_FAVICON_DOMAINS.has(
    domain.replace(/^www\./, ""),
  );
  const suppliedBrandLogo = providedLogo && !isFavicon(providedLogo)
    ? { src: providedLogo, scale: 1 }
    : null;
  const suppliedFavicon = providedLogo && isFavicon(providedLogo)
    ? { src: providedLogo, scale: 1.12 }
    : null;
  const sources = [
    brandLogo.value?.isLocal ? brandLogo.value : null,
    suppliedBrandLogo,
    brandLogo.value?.isLocal ? null : brandLogo.value,
    !skipFaviconSources && suppliedFavicon,
    !skipFaviconSources && domain && {
      src: resolveSiteLogo({ url: props.url }),
      scale: 1.12,
    },
    !skipFaviconSources && domain && {
      src: `https://icons.duckduckgo.com/ip3/${domain}.ico`,
      scale: 1.14,
    },
    !skipFaviconSources && domain && {
      src: `https://${domain}/favicon.ico`,
      scale: 1.14,
    },
  ];

  return sources.filter(
    (source, index, allSources) =>
      source?.src?.trim() &&
      allSources.findIndex((candidate) => candidate?.src === source.src) === index,
  );
});
const imageSrc = computed(
  () => logoSources.value[sourceIndex.value]?.src || "",
);
const logoScale = computed(() => {
  const explicitScale = Number(props.scale);
  if (Number.isFinite(explicitScale)) {
    return Math.min(1.35, Math.max(1, explicitScale));
  }

  return logoSources.value[sourceIndex.value]?.scale || 1;
});
const initial = computed(() => Array.from(label.value)[0]?.toUpperCase() || "?");
const pixelSize = computed(() => ({ sm: 28, md: 36, lg: 48 })[props.size]);

watch(
  () => logoSources.value.map((source) => source.src).join("|"),
  () => {
    imageFailed.value = false;
    imageLoaded.value = false;
    sourceIndex.value = 0;
  },
  { immediate: true },
);

watch(imageSrc, () => {
  imageFailed.value = false;
  imageLoaded.value = false;
});

function tryNextLogo() {
  if (sourceIndex.value < logoSources.value.length - 1) {
    sourceIndex.value += 1;
    return;
  }

  imageFailed.value = true;
}

function handleImageLoad(event) {
  const source = imageSrc.value;
  const image = event.currentTarget;
  if (
    !isSvgSource(source) &&
    (image.naturalWidth < 32 || image.naturalHeight < 32)
  ) {
    tryNextLogo();
    return;
  }

  imageLoaded.value = true;
}

function handleImageError() {
  tryNextLogo();
}
</script>

<style scoped>
.site-logo {
  display: block;
  flex: 0 0 auto;
  object-fit: contain;
  object-position: center;
  transform-origin: center;
}

.site-logo--tight {
  transform-origin: center;
}

.site-logo--pending {
  opacity: 0;
}

.site-logo--sm {
  width: 28px;
  height: 28px;
}

.site-logo--md {
  width: 36px;
  height: 36px;
}

.site-logo--lg {
  width: 48px;
  height: 48px;
}

.site-logo--fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  color: #475569;
  font-size: 18px;
  font-weight: 600;
  line-height: 1;
}
</style>
