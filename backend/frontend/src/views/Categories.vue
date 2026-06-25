<template>
  <main class="list-page">
    <header>
      <RouterLink to="/">返回首页</RouterLink>
      <h1>分类导航</h1>
      <p>按方向浏览系统收录的网站资源。</p>
    </header>
    <section class="category-list">
      <article v-for="category in categories" :key="category.id">
        <h2>{{ category.name }}</h2>
        <span>{{ category.sites?.length || 0 }} 个网站</span>
        <RouterLink :to="'/category/' + category.id">查看</RouterLink>
      </article>
    </section>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { navAPI } from '@/utils/api'

const categories = ref([])
onMounted(async () => {
  const res = await navAPI.getNavData()
  categories.value = res.data?.data?.categories || []
})
</script>

<style scoped>
.list-page { min-height: 100vh; background: #f7f8fb; padding: 28px; color: #172033; }
header, .category-list { max-width: 1100px; margin: 0 auto; }
a { color: #2563eb; text-decoration: none; }
h1 { margin: 12px 0 8px; font-size: 30px; }
p { color: #64748b; }
.category-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
article { background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 18px; }
h2 { margin: 0 0 10px; font-size: 18px; }
span { display: block; margin-bottom: 14px; color: #64748b; }
</style>
