<template>
  <section
    class="hero-search reveal-on-scroll"
    :class="{ 'engine-menu-open': engineMenuOpen }"
    data-testid="home-hero"
    aria-labelledby="home-hero-title"
  >
    <div class="hero-copy">
      <ParticleText
        v-if="false"
        id="home-hero-title-particles"
        class="hero-particle-title"
        :style="{ '--particle-title-color': particleTitleColor }"
        text="根据你的职业，推荐最适合的工具"
      />
      <h1 id="home-hero-title">
        <span>根据你的职业，</span>
        <span>推荐<strong>最适合</strong>的资源</span>
      </h1>
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
    ? "#0A234A"
    : "var(--heading-text-color, var(--app-text-primary))";
});
</script>

<style scoped>
.hero-search {
  display: grid;
  position: relative;
  width: 100%;
  height: 100%;
  min-height: clamp(420px, 54vh, 540px);
  place-items: center;
  align-content: center;
  gap: 46px;
  box-sizing: border-box;
  padding: 0 20px;
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
  gap: 24px;
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
  color: #0a234a;
  font-family: "Songti SC", "STSong", "SimSun", "Noto Serif SC", serif;
  font-size: clamp(52px, 4.2vw, 70px);
  font-weight: 600;
  line-height: 1.28;
  letter-spacing: 0.025em;
  white-space: nowrap;
}

h1 span {
  display: block;
}

h1 strong {
  color: var(--primary);
  font-weight: inherit;
}

.hero-copy p {
  margin: 0;
  max-width: 900px;
  color: #566a89;
  font-family: "Songti SC", "STSong", "SimSun", serif;
  font-size: clamp(17px, 1.25vw, 20px);
  line-height: 1.5;
}

.hero-search__bar {
  width: min(1000px, calc(100vw - 360px));
  justify-self: center;
}

.hero-search__search-area {
  display: grid;
  width: 100%;
  place-items: center;
}

:deep(.hero-search__bar .search-bar) {
  width: 100%;
  max-width: none;
  min-height: 70px;
  border-color: rgba(220, 230, 245, 0.7);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 8px 25px rgba(80, 120, 180, 0.1);
  padding: 5px 6px;
}

:deep(.hero-search__bar .engine-picker) {
  flex-basis: 160px;
  height: 58px;
  border-right: 1px solid rgba(210, 223, 244, 0.95);
  padding-right: 12px;
}

:deep(.hero-search__bar .engine-picker__trigger) {
  border-color: transparent;
  background: rgba(247, 250, 255, 0.82);
  color: #213b65;
  font-family: "Songti SC", "STSong", "SimSun", serif;
  font-size: 17px;
}

:deep(.hero-search__bar .engine-picker__chevron) {
  color: #0a234a;
}

:deep(.hero-search__bar .search-input) {
  height: 58px;
  color: #213b65;
  font-family: "Songti SC", "STSong", "SimSun", serif;
  font-size: 18px;
}

:deep(.hero-search__bar .search-input::placeholder) {
  color: #8596b3;
  opacity: 1;
}

:deep(.hero-search__bar .search-button) {
  flex-basis: 58px;
  width: 58px;
  height: 58px;
  min-width: 58px;
  background: var(--primary);
  box-shadow: 0 7px 16px color-mix(in srgb, var(--primary) 24%, transparent);
}

:deep(.hero-search__bar .search-button:hover),
:deep(.hero-search__bar .search-button:focus-visible) {
  background: var(--primary-hover);
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
    white-space: normal;
  }

  .hero-search__bar {
    width: min(100%, calc(100vw - 32px));
  }
}
</style>
