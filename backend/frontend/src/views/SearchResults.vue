<template>
  <main class="list-page">
    <header>
      <RouterLink to="/">返回首页</RouterLink>
      <h1>搜索结果</h1>
      <form @submit.prevent="runSearch">
        <input v-model="query" placeholder="搜索 AI 工具、学习资料、开发网站" />
        <button>搜索</button>
      </form>
    </header>
    <section class="site-grid">
      <article v-for="site in sites" :key="site.id" class="site-card">
        <img :src="site.logo_url || fallbackLogo(site)" :alt="site.name" />
        <div>
          <h2>{{ site.name }}</h2>
          <p>{{ site.description || site.category_name || '系统收录网站' }}</p>
          <RouterLink :to="'/site/' + site.id">查看详情</RouterLink>
        </div>
      </article>
    </section>
    <p v-if="!loading && sites.length === 0" class="empty">暂无匹配结果</p>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { navAPI } from '@/utils/api'

const route = useRoute()
const router = useRouter()
const query = ref(route.query.q || '')
const sites = ref([])
const loading = ref(false)

const fallbackLogo = (site) => `https://www.google.com/s2/favicons?sz=128&domain_url=${encodeURIComponent(site.url || '')}`

const runSearch = async () => {
  router.replace({ path: '/search', query: { q: query.value } })
  loading.value = true
  try {
    const res = await navAPI.search(query.value)
    sites.value = res.data?.data?.items || []
  } finally {
    loading.value = false
  }
}

onMounted(runSearch)
</script>

<style scoped>
.list-page { min-height: 100vh; background: #f7f8fb; padding: 28px; color: #172033; }
header { max-width: 1100px; margin: 0 auto 22px; }
a { color: #2563eb; text-decoration: none; }
h1 { margin: 12px 0 16px; font-size: 30px; }
form { display: flex; gap: 10px; max-width: 680px; }
input { flex: 1; height: 44px; border: 1px solid #dbe1ec; border-radius: 6px; padding: 0 12px; }
button { width: 88px; border: 0; border-radius: 6px; background: #111827; color: #fff; font-weight: 700; }
.site-grid { max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
.site-card { display: flex; gap: 12px; background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 14px; }
img { width: 42px; height: 42px; border-radius: 8px; }
h2 { margin: 0 0 6px; font-size: 17px; }
p { margin: 0 0 10px; color: #64748b; font-size: 13px; }
.empty { max-width: 1100px; margin: 20px auto; color: #64748b; }
@media (max-width: 600px) { form { flex-direction: column; } button { width: 100%; height: 42px; } }
</style>
