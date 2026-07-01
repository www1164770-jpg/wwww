<template>
  <section class="hero-search">
    <div class="hero-copy">
      <h1>根据你的职业，推荐最适合的 AI 工具</h1>
      <p>
        收集、筛选和推荐高质量网站资源，让学习、工作、创作和项目开发更高效。
      </p>
    </div>

    <form class="search-box" @submit.prevent="$emit('search')">
      <input
        :value="modelValue"
        type="search"
        placeholder="搜索 AI 工具、网站或使用场景，例如：论文写作、编程、PPT、设计"
        @input="$emit('update:modelValue', $event.target.value)"
      />
      <button type="submit" aria-label="搜索">搜索</button>
    </form>

    <p class="hero-stats">已收录工具 · 热门分类 · 个性化推荐已开启</p>
  </section>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: "",
  },
});

defineEmits(["update:modelValue", "search", "show-all", "show-favorites"]);
</script>

<style scoped>
.hero-search {
  display: grid;
  min-height: clamp(520px, 62vh, 620px);
  place-items: center;
  align-content: center;
  gap: 26px;
  padding: 92px 20px 76px;
  background:
    radial-gradient(
      circle at 10% 20%,
      rgba(191, 245, 237, 0.45),
      transparent 28%
    ),
    radial-gradient(
      circle at 90% 35%,
      rgba(255, 112, 88, 0.2),
      transparent 30%
    ),
    linear-gradient(180deg, #ffffff 0%, #ffffff 100%);
}

.hero-copy {
  display: grid;
  justify-items: center;
  gap: 18px;
  max-width: 900px;
  text-align: center;
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(42px, 7vw, 64px);
  font-weight: 800;
  line-height: 1.08;
}

.hero-copy p {
  margin: 0;
  max-width: 680px;
  color: var(--color-text);
  font-size: 18px;
  line-height: 1.75;
}

.search-box {
  display: grid;
  grid-template-columns: 1fr auto;
  width: min(720px, 100%);
  min-height: 64px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: #ffffff;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.search-box:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 18px 45px rgba(255, 112, 88, 0.14);
}

.search-box input {
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 0 6px 0 26px;
  color: var(--color-heading);
  outline: 0;
}

.search-box button {
  align-self: center;
  width: 52px;
  height: 52px;
  min-width: 52px;
  margin-right: 6px;
  border: 0;
  border-radius: 50%;
  color: #ffffff;
  background: var(--color-primary);
  font-size: 0;
  box-shadow: 0 12px 24px rgba(255, 112, 88, 0.22);
}

.search-box button::before {
  content: "";
  display: block;
  width: 17px;
  height: 17px;
  margin: 0 auto;
  border: 2px solid currentColor;
  border-radius: 50%;
  box-shadow: 8px 8px 0 -6px currentColor;
  transform: rotate(-15deg);
}

.hero-stats {
  margin: 0;
  color: var(--color-muted);
  font-size: 14px;
  font-weight: 700;
}

@media (max-width: 640px) {
  .hero-search {
    min-height: 500px;
    padding-top: 64px;
  }

  .search-box {
    min-height: 58px;
  }

  .search-box input {
    padding-left: 18px;
    font-size: 14px;
  }

  .search-box button {
    width: 46px;
    height: 46px;
    min-width: 46px;
  }
}
</style>
