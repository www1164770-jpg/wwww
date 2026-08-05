<template>
  <section
    class="hero-search reveal-on-scroll"
    :class="{ 'engine-menu-open': engineMenuOpen }"
    data-testid="home-hero"
    aria-labelledby="home-hero-title"
  >
    <div class="hero-copy">
      <h1 id="home-hero-title">根据你的职业，推荐最适合的工具</h1>
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
import { ref } from "vue";
import SearchBar from "../common/SearchBar.vue";

defineProps({
  modelValue: {
    type: String,
    default: "",
  },
});

defineEmits(["update:modelValue", "search", "show-all", "show-favorites"]);

const engineMenuOpen = ref(false);
</script>

<style scoped>
.hero-search {
  display: grid;
  position: relative;
  min-height: clamp(380px, 46vh, 480px);
  place-items: center;
  align-content: center;
  gap: 28px;
  padding: 100px 20px 48px;
  overflow: visible;
  background:
    radial-gradient(
      circle at 14% 18%,
      rgba(191, 245, 237, 0.42),
      transparent 30%
    ),
    radial-gradient(
      circle at 88% 28%,
      rgba(255, 112, 88, 0.18),
      transparent 32%
    ),
    linear-gradient(180deg, #ffffff 0%, #fffdfc 54%, #ffffff 100%);
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
  justify-items: center;
  gap: 18px;
  max-width: 930px;
  text-align: center;
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(40px, 7vw, 68px);
  font-weight: 850;
  line-height: 1.08;
}

.hero-copy p {
  margin: 0;
  max-width: 700px;
  color: var(--color-text);
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
  color: var(--color-muted);
  font-size: 14px;
  font-weight: 750;
}

@media (max-width: 640px) {
  .hero-search {
    min-height: auto;
    padding: 80px 16px 36px;
  }
}
</style>
