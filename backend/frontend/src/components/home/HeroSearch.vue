<template>
  <section
    class="hero-search reveal-on-scroll"
    :class="{ 'engine-menu-open': engineMenuOpen }"
    data-testid="home-hero"
    aria-labelledby="home-hero-title"
  >
    <div class="hero-copy">
      <ParticleText
        id="home-hero-title"
        class="hero-particle-title"
        :style="{ '--particle-title-color': particleTitleColor }"
        text="根据你的职业，推荐最适合的工具"
      />
      <p>
        收集、筛选和推荐高质量网站资源，让学习、工作、创作和项目开发更高效。
      </p>
    </div>

    <div
      class="hero-search__search-area"
      :class="{ 'engine-menu-open': engineMenuOpen }"
    >
      <SearchBar
        :model-value="modelValue"
        class="hero-search__bar"
        placeholder="搜索工具、网站或使用场景，例如：论文写作、编程、PPT、设计"
        :navigate-on-submit="false"
        @update:model-value="$emit('update:modelValue', $event)"
        @search="$emit('search', $event)"
        @engine-menu-change="engineMenuOpen = $event"
      />
    </div>

    <p class="hero-stats">已收录工具 · 热门分类 · 个性化推荐已开启</p>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import { usePersonalizationStore } from "../../stores/personalization";
import ParticleText from "./ParticleText.vue";
import SearchBar from "../common/SearchBar.vue";

defineProps({
  modelValue: {
    type: String,
    default: "",
  },
});

defineEmits(["update:modelValue", "search", "show-all", "show-favorites"]);

const engineMenuOpen = ref(false);
const personalizationStore = usePersonalizationStore();
const particleTitleColor = computed(() => {
  const settings = personalizationStore.settings;
  const usesDefaultAppearance =
    settings?.themeKey === "default" &&
    settings?.background?.type === "default" &&
    settings?.typography?.mode === "auto";

  return usesDefaultAppearance
    ? "#111827"
    : "var(--heading-text-color, var(--app-text-primary))";
});
</script>

<style scoped>
.hero-search {
  display: grid;
  position: relative;
  width: 100%;
  height: 100%;
  min-height: clamp(380px, 46vh, 480px);
  place-items: center;
  align-content: center;
  gap: 28px;
  box-sizing: border-box;
  padding: 32px 20px 24px;
  overflow: visible;
  background: var(--app-page-bg);
}

.hero-search.reveal-on-scroll {
  opacity: 1;
  transform: none;
}

.hero-search.engine-menu-open {
  z-index: 50;
}

.hero-copy {
  display: grid;
  width: min(var(--container), calc(100% - 40px));
  justify-items: center;
  gap: 18px;
  text-align: center;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

h1 {
  margin: 0;
  color: var(--app-text-primary);
  font-size: clamp(64px, 5.1vw, 88px);
  font-weight: 900;
  line-height: 1.1;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.hero-copy p {
  margin: 0;
  max-width: 700px;
  color: var(--app-text-secondary);
  font-size: 18px;
  line-height: 1.75;
}

.hero-search__bar {
  width: min(820px, calc(100vw - 40px));
  justify-self: center;
}

.hero-search__search-area {
  display: grid;
  width: 100%;
  place-items: center;
}

.hero-stats {
  margin: 0;
  color: var(--app-text-muted);
  font-size: 14px;
  font-weight: 750;
}

@media (max-width: 640px) {
  .hero-search {
    min-height: auto;
    gap: 22px;
    padding: 24px 16px 20px;
  }
}

@media (max-width: 767px) {
  .hero-copy {
    width: 100%;
  }

  h1 {
    font-size: clamp(34px, 10vw, 44px);
    white-space: nowrap;
  }
}
</style>
