<template>
  <section class="hero-search">
    <div class="hero-copy">
      <p class="eyebrow">AI 工具导航</p>
      <h1>根据你的职业，推荐最适合的 AI 工具</h1>
      <p>搜索工具、职业场景或任务关键词，快速找到学习、办公、创作和编程入口。</p>
    </div>

    <form class="search-box" @submit.prevent="$emit('search')">
      <input
        :value="modelValue"
        type="search"
        placeholder="搜索 AI 工具、网站或使用场景，例如：论文写作、编程、PPT、设计"
        @input="$emit('update:modelValue', $event.target.value)"
      >
      <button type="submit">搜索</button>
    </form>

    <div class="quick-actions" aria-label="首页快捷入口">
      <button type="button" @click="$emit('show-all')">浏览全部工具</button>
      <button type="button" @click="$emit('show-favorites')">查看收藏</button>
      <RouterLink to="/publish">提交网站</RouterLink>
    </div>
  </section>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

defineEmits(['update:modelValue', 'search', 'show-all', 'show-favorites'])
</script>

<style scoped>
.hero-search {
  display: grid;
  gap: 24px;
  padding: 72px min(6vw, 72px) 40px;
}

.hero-copy {
  max-width: 760px;
}

.eyebrow {
  margin: 0 0 12px;
  color: #1769aa;
  font-weight: 700;
}

h1 {
  margin: 0;
  max-width: 780px;
  color: #18212f;
  font-size: clamp(38px, 6vw, 72px);
  line-height: 1.02;
}

.hero-copy p:last-child {
  margin: 18px 0 0;
  max-width: 640px;
  color: #5a6472;
  font-size: 18px;
  line-height: 1.7;
}

.search-box {
  display: grid;
  grid-template-columns: 1fr auto;
  max-width: 760px;
  overflow: hidden;
  border: 1px solid #d6deea;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 18px 44px rgba(31, 53, 84, 0.12);
}

.search-box input {
  min-width: 0;
  border: 0;
  padding: 18px 20px;
  font: inherit;
  outline: 0;
}

.search-box button,
.quick-actions button,
.quick-actions a {
  border: 0;
  border-radius: 6px;
  padding: 12px 18px;
  color: #fff;
  background: #18212f;
  font: inherit;
  text-decoration: none;
  cursor: pointer;
}

.search-box button {
  margin: 6px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.quick-actions button,
.quick-actions a {
  color: #18212f;
  background: #edf3fa;
}

@media (max-width: 640px) {
  .hero-search {
    padding-inline: 20px;
  }

  .search-box {
    grid-template-columns: 1fr;
  }
}
</style>
