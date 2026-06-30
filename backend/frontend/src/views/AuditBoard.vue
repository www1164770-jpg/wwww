<template>
  <div class="audit-container">
    <header class="audit-header">
      <h2>🚀 站点审核工作台</h2>
      <p>
        当前有 <strong>{{ pendingSites.length }}</strong> 个站点等待您的批阅
      </p>
    </header>

    <div v-if="pendingSites.length === 0" class="empty-state">
      🎉 太棒了！所有的待办都已经清空啦！
    </div>

    <div v-else class="bento-grid">
      <div v-for="site in pendingSites" :key="site.id" class="bento-card">
        <div class="card-content">
          <span class="source-badge">{{ site.source || "爬虫采集" }}</span>
          <h3 class="site-title">{{ site.name }}</h3>
          <a :href="site.url" target="_blank" class="site-url">{{
            site.url
          }}</a>
          <p class="site-desc">{{ site.description }}</p>
        </div>

        <div class="card-actions">
          <button class="btn reject" @click="handleAudit(site.id, 'reject')">
            ❌ 驳回
          </button>
          <button class="btn approve" @click="handleAudit(site.id, 'approve')">
            ✅ 批准上线
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { API_BASE_URL } from "../utils/api";

// 待审核数据源
const pendingSites = ref([]);

// 1. 页面加载时抓取数据
const fetchPendingSites = async () => {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/pending-sites`);
    pendingSites.value = await res.json();
  } catch (error) {
    console.error("获取待审核列表失败:", error);
  }
};

// 2. 处理审核操作 (通过/拒绝)
const handleAudit = async (siteId, action) => {
  try {
    const res = await fetch(`${API_BASE_URL}/admin/audit-site/${siteId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });

    if (res.ok) {
      // 审核成功后，利用 filter 从前端列表中移除这张卡片，不需要重新发请求刷新整个列表
      pendingSites.value = pendingSites.value.filter(
        (site) => site.id !== siteId,
      );
    }
  } catch (error) {
    console.error(`执行 ${action} 操作失败:`, error);
  }
};

// 组件挂载时触发请求
onMounted(() => {
  fetchPendingSites();
});
</script>
<style scoped>
/* 容器基础设置 */
.audit-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.audit-header {
  margin-bottom: 2rem;
  text-align: center;
}

.empty-state {
  text-align: center;
  padding: 4rem;
  background-color: var(--bg-secondary, #f3f4f6);
  border-radius: 16px;
  color: var(--text-secondary, #6b7280);
  font-size: 1.2rem;
}

/* 🍱 核心便当盒布局 (CSS Grid) */
.bento-grid {
  display: grid;
  /* 自动响应式：每列最小 320px，排不下自动换行 */
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

/* 卡片样式与过渡动画 */
.bento-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background-color: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 20px; /* 圆润的边角 */
  padding: 20px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    opacity 0.3s ease;
}

.bento-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

/* 卡片内部元素 */
.source-badge {
  display: inline-block;
  font-size: 0.75rem;
  padding: 4px 8px;
  background-color: #fce7f3;
  color: #db2777;
  border-radius: 999px;
  margin-bottom: 12px;
  font-weight: bold;
}

.site-title {
  font-size: 1.25rem;
  margin: 0 0 8px 0;
  color: var(--text-primary, #111827);
}

.site-url {
  font-size: 0.875rem;
  color: #3b82f6;
  text-decoration: none;
  word-break: break-all;
}

.site-url:hover {
  text-decoration: underline;
}

.site-desc {
  font-size: 0.9rem;
  color: var(--text-secondary, #6b7280);
  margin-top: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2; /* 限制描述最多两行 */
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 操作按钮布局 */
.card-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.btn {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.2s;
}

.btn:hover {
  filter: brightness(0.95);
}

.reject {
  background-color: #fee2e2;
  color: #dc2626;
}

.approve {
  background-color: #dcfce3;
  color: #16a34a;
}
</style>
