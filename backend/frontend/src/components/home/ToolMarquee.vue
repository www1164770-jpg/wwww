<template>
  <section class="tool-marquee" aria-label="常用工具品牌">
    <div class="marquee-track">
      <span v-for="tool in tools" :key="tool">{{ tool }}</span>
    </div>
  </section>
</template>

<script setup>
const tools = [
  "ChatGPT",
  "Claude",
  "Notion",
  "Canva",
  "GitHub",
  "Figma",
  "掘金",
  "知乎",
  "Bilibili",
  "LeetCode",
  "MDN",
  "Vercel",
  "飞书",
  "ProcessOn",
  "Iconfont",
  "Unsplash",
];
</script>

<style scoped>
.tool-marquee {
  overflow-x: auto;
  border-top: 1px solid var(--color-border-soft);
  border-bottom: 1px solid var(--color-border-soft);
  background: #ffffff;
  scrollbar-width: none;
}

.tool-marquee::-webkit-scrollbar {
  display: none;
}

.marquee-track {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: clamp(26px, 4vw, 46px);
  width: max-content;
  min-width: 100%;
  min-height: 96px;
  padding: 0 32px;
}

span {
  color: #94a3b8;
  font-size: clamp(24px, 3vw, 28px);
  font-weight: 700;
  white-space: nowrap;
  transition: color var(--transition);
}

span:hover {
  color: var(--color-heading);
}
</style>
