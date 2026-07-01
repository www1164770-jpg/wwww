<template>
  <footer class="app-footer">
    <div class="brand">智慧导航</div>
    <div class="links">
      <span>友情链接</span>
      <span>版权所有 2026</span>
      <span>备案信息占位</span>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  width: min(1200px, calc(100% - 40px));
  margin: 0 auto;
  padding: 32px 0;
  color: var(--color-muted);
  border-top: 1px solid var(--color-border-soft);
}

.brand {
  color: var(--color-heading);
  font-weight: 850;
}

.links {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
}

@media (max-width: 720px) {
  .app-footer {
    flex-direction: column;
  }
}
</style>
