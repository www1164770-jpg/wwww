<template>
  <section class="tool-marquee" aria-label="常用工具品牌">
    <div class="marquee-shell">
      <div class="marquee-track">
        <span v-for="tool in tools" :key="tool">{{ tool }}</span>
        <span v-for="tool in tools" :key="`${tool}-copy`">{{ tool }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
const tools = [
  "ChatGPT",
  "Claude",
  "Midjourney",
  "Notion",
  "Canva",
  "GitHub",
  "Figma",
  "飞书",
  "掘金",
  "知乎",
  "Bilibili",
  "LeetCode",
  "MDN",
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
  padding: 18px 0;
}

.marquee-shell {
  position: relative;
  overflow: hidden;
}

.marquee-shell::before,
.marquee-shell::after {
  position: absolute;
  top: 0;
  z-index: 1;
  width: 96px;
  height: 100%;
  content: "";
  pointer-events: none;
}

.marquee-shell::before {
  left: 0;
  background: linear-gradient(90deg, #ffffff 0%, rgba(255, 255, 255, 0) 100%);
}

.marquee-shell::after {
  right: 0;
  background: linear-gradient(270deg, #ffffff 0%, rgba(255, 255, 255, 0) 100%);
}

.marquee-track {
  display: flex;
  align-items: center;
  gap: 18px;
  width: max-content;
  min-height: 84px;
  padding: 0 32px;
  animation: marquee 40s linear infinite;
}

span {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  border: 1px solid var(--color-border-soft);
  border-radius: var(--radius-pill);
  background: #ffffff;
  color: var(--color-text);
  padding: 0 18px;
  font-size: clamp(16px, 2vw, 20px);
  font-weight: 800;
  white-space: nowrap;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.04);
  transition:
    color var(--transition),
    border-color var(--transition),
    transform var(--transition);
}

span:hover {
  border-color: rgba(255, 112, 88, 0.32);
  color: var(--color-primary);
  transform: translateY(-2px);
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
