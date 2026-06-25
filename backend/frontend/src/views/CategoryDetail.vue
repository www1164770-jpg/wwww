<template>
  <main class="list-page">
    <header>
      <RouterLink to="/categories">返回分类</RouterLink>
      <h1>{{ category?.name || '分类网站' }}</h1>
    </header>
    <section class="site-grid">
      <article v-for="site in sites" :key="site.id" class="site-card">
        <img :src="site.logo_url || fallbackLogo(site)" :alt="site.name" />
        <h2>{{ site.name }}</h2>
        <p>{{ site.description || '系统收录网站' }}</p>
        <RouterLink :to="'/site/' + site.id">查看详情</RouterLink>
      </article>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { navAPI } from '@/utils/api'

const route = useRoute()
const categories = ref([])
const category = computed(() => categories.value.find(item => String(item.id) === String(route.params.id)))
const sites = computed(() => category.value?.sites || [])
const fallbackLogo = (site) => `https://www.google.com/s2/favicons?sz=128&domain_url=${encodeURIComponent(site.url || '')}`

onMounted(async () => {
  const res = await navAPI.getNavData()
  categories.value = res.data?.data?.categories || []
})
</script>

<style scoped>
.list-page { min-height: 100vh; background: #f7f8fb; padding: 28px; color: #172033; }
header, .site-grid { max-width: 1100px; margin: 0 auto; }
a { color: #2563eb; text-decoration: none; }
h1 { margin: 12px 0 18px; font-size: 30px; }
.site-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.site-card { background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 16px; }
img { width: 42px; height: 42px; border-radius: 8px; }
h2 { margin: 12px 0 8px; font-size: 18px; }
p { color: #64748b; min-height: 38px; }
</style>
