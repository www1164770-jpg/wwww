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
.admin-page { padding: 40px; max-width: 1200px; margin: 0 auto; color: #1e293b; }
.admin-header { display: flex; justify-content: space-between; align-items: center; padding: 20px 30px; margin-bottom: 30px; background: white; border-radius: 16px; }
.admin-content { display: flex; gap: 20px; }
.stat-card { flex: 1; padding: 30px; background: white; border-radius: 16px; text-align: center; }
.stat-num { font-size: 36px; font-weight: bold; color: #3b82f6; margin-top: 10px; }
</style>