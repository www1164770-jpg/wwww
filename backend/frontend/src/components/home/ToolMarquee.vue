<template>
  <section class="tool-marquee" aria-label="常用工具品牌">
    <div class="marquee-track">
      <span v-for="tool in tools" :key="tool">{{ tool }}</span>
      <span v-for="tool in tools" :key="`${tool}-copy`">{{ tool }}</span>
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
  overflow: hidden;
  border-top: 1px solid var(--color-border-soft);
  border-bottom: 1px solid var(--color-border-soft);
  background: #ffffff;
}

.marquee-track {
  display: flex;
  align-items: center;
  gap: 44px;
  width: max-content;
  min-height: 100px;
  padding: 0 32px;
  animation: marquee 38s linear infinite;
}

span {
  color: var(--color-muted);
  font-size: clamp(20px, 3vw, 26px);
  font-weight: 800;
  white-space: nowrap;
  transition: color var(--transition);
}

span:hover {
  color: var(--color-heading);
}

@keyframes marquee {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .marquee-track {
    width: auto;
    flex-wrap: wrap;
    animation: none;
  }
}
</style>
