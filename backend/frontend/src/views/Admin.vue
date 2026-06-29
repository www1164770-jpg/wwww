<template>
  <div class="admin-page">
    <div class="admin-header block-shadow">
      <h1>🛡️ 智汇导航 - 管理后台</h1>
      <button class="btn-cancel" @click="$router.push('/')">返回前台首页</button>
    </div>
    
    <div class="admin-content">
      <div class="stat-card block-shadow">
        <h3>今日新增用户</h3>
        <p class="stat-num">0</p>
      </div>
      <div class="stat-card block-shadow">
        <h3>待审核文章</h3>
        <p class="stat-num">0</p>
      </div>
      <div class="stat-card block-shadow">
        <h3>总访问量</h3>
        <p class="stat-num">0</p>
      </div>
    </div>
  </div>
</template>

<script setup>
// 这里后续可以接入我们之前写的 /api/admin/stats 接口
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  padding: 48px clamp(18px, 4vw, 48px);
  max-width: 1180px;
  margin: 0 auto;
  color: var(--mono-text);
  animation: mono-rise-in 0.64s var(--mono-ease);
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  padding: 22px 28px;
  margin-bottom: 24px;
  background: var(--mono-surface) !important;
  border: 1px solid var(--mono-border);
  border-radius: var(--mono-radius-lg);
  box-shadow: var(--mono-shadow-sm);
  backdrop-filter: blur(18px);
}

.admin-header h1 {
  margin: 0;
  font-size: clamp(24px, 3vw, 34px);
  font-weight: 820;
  letter-spacing: -0.06em;
  filter: grayscale(1);
}

.admin-content {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.stat-card {
  padding: 30px;
  background: var(--mono-surface) !important;
  border: 1px solid var(--mono-border);
  border-radius: var(--mono-radius-lg);
  text-align: center;
  box-shadow: var(--mono-shadow-sm);
  transition: transform var(--mono-base) var(--mono-ease), box-shadow var(--mono-base) var(--mono-ease), border-color var(--mono-base) var(--mono-ease);
}

.stat-card:hover {
  transform: translateY(-5px);
  border-color: var(--mono-border-strong);
  box-shadow: var(--mono-shadow-md);
}

.stat-card h3 {
  margin: 0;
  color: var(--mono-muted);
  font-size: 14px;
  font-weight: 650;
}

.stat-num {
  margin: 14px 0 0;
  color: var(--mono-text);
  font-size: 42px;
  font-weight: 860;
  letter-spacing: -0.06em;
}

@media (max-width: 760px) {
  .admin-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .admin-content {
    grid-template-columns: 1fr;
  }
}
</style>
