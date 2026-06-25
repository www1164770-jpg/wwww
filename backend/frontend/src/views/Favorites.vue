<template>
  <main class="list-page">
    <header>
      <RouterLink to="/">返回首页</RouterLink>
      <h1>我的收藏</h1>
      <p>登录后收藏的网站会在这里集中展示。</p>
    </header>
    <section v-if="sites.length" class="site-grid">
      <article v-for="site in sites" :key="site.id" class="site-card">
        <img :src="site.logo_url || fallbackLogo(site)" :alt="site.name" />
        <h2>{{ site.name }}</h2>
        <p>{{ site.description || site.category_name || '系统收录网站' }}</p>
        <RouterLink :to="'/site/' + site.id">查看详情</RouterLink>
      </article>
    </section>
    <section v-else class="empty">
      <p>{{ message }}</p>
      <RouterLink to="/">去系统网站收藏</RouterLink>
    </section>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { navAPI } from '@/utils/api'

const sites = ref([])
const message = ref('暂无收藏')
const fallbackLogo = (site) => `https://www.google.com/s2/favicons?sz=128&domain_url=${encodeURIComponent(site.url || '')}`

onMounted(async () => {
  try {
    const nav = await navAPI.getNavData()
    const allSites = nav.data?.data?.sites || []
    const fav = await navAPI.getFavorites()
    const ids = (fav.data?.data || []).map(item => item.website_id)
    sites.value = allSites.filter(site => ids.includes(site.id))
    if (!sites.value.length) message.value = '你还没有收藏网站'
  } catch (_) {
    message.value = '请先登录后查看收藏'
  }
})
</script>

<style scoped>
.list-page { min-height: 100vh; background: #f7f8fb; padding: 28px; color: #172033; }
header, .site-grid, .empty { max-width: 1100px; margin: 0 auto; }
a { color: #2563eb; text-decoration: none; }
h1 { margin: 12px 0 8px; font-size: 30px; }
p { color: #64748b; }
.site-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.site-card { background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 16px; }
img { width: 42px; height: 42px; border-radius: 8px; }
h2 { margin: 12px 0 8px; font-size: 18px; }
.empty { background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 22px; }
</style>
