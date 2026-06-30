<template>
  <footer class="app-footer">
    <div>AI Nav</div>
    <div class="links">
      <span>Friendly links</span>
      <span>Copyright 2026</span>
      <span>ICP placeholder</span>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 28px clamp(18px, 5vw, 64px);
  color: #6b7280;
  border-top: 1px solid #e5e7eb;
}
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
@media (max-width: 720px) {
  .app-footer {
    flex-direction: column;
  }
}
</style>
