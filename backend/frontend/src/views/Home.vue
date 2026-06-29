<template>
  <div class="home-page" :class="{ dark: isDarkMode }">
    <header class="topbar">
      <RouterLink class="brand" to="/">智慧导航</RouterLink>
      <nav aria-label="主导航">
        <a href="#tools">工具库</a>
        <a href="#career">职业推荐</a>
        <a href="#ranking">热门榜单</a>
        <a href="#articles">资讯文章</a>
        <a href="#about">关于本站</a>
      </nav>
      <div class="topbar-actions">
        <button type="button" @click="showAppearanceModal = true">外观</button>
        <RouterLink v-if="isLoggedIn" to="/profile">个人中心</RouterLink>
        <button v-else type="button" @click="showLoginModal = true">登录</button>
      </div>
    </header>

    <HeroSearch
      v-model="searchQuery"
      @search="doSearch"
      @show-all="showAllTools"
      @show-favorites="showFavorites"
    />

    <CareerRecommend
      :active-career="activeCareer"
      @select-career="selectCareer"
    />

    <section id="tools" class="tools-section">
      <div class="section-heading">
        <p>工具库</p>
        <h2>{{ activeCareer ? `${activeCareer} 推荐工具` : '热门 AI 工具与效率网站' }}</h2>
        <button type="button" @click="openSiteModal()">提交网站</button>
      </div>

      <PopularCategories
        :categories="categoryOptions"
        :active-category="activeCategoryId"
        @select-category="selectCategory"
      />

      <div class="tool-grid">
        <ToolCard
          v-for="site in filteredTools"
          :key="site.id"
          :site="site"
          :is-favorited="favoriteSiteIds.includes(site.id)"
          @visit="visitSite"
          @toggle-favorite="toggleFavorite"
        />
      </div>

      <p v-if="filteredTools.length === 0" class="empty-state">暂时没有匹配的工具，换个关键词试试。</p>
    </section>

    <FavoriteStack :sites="favoriteStackTools" @visit="visitSite" />

    <section id="ranking" class="info-band">
      <div>
        <p>热门榜单</p>
        <h2>本周高频访问</h2>
      </div>
      <ol>
        <li v-for="site in rankingTools" :key="site.id">
          <span>{{ site.name }}</span>
          <strong>{{ site.clicks || 0 }} 次</strong>
        </li>
      </ol>
    </section>

    <section id="articles" class="info-band articles">
      <div>
        <p>资讯文章</p>
        <h2>AI 工具使用灵感</h2>
      </div>
      <div class="article-list">
        <article v-for="article in articles" :key="article.title">
          <h3>{{ article.title }}</h3>
          <span>{{ article.summary }}</span>
        </article>
      </div>
    </section>

    <section id="about" class="about-band">
      <p>关于本站</p>
      <h2>面向学生、程序员、设计师和运营的 AI 工具导航平台。</h2>
    </section>

    <LoginModal :visible="showLoginModal" @close="showLoginModal = false" />
    <SiteFormModal
      :visible="showSiteModal"
      :site="editingSite"
      :categories="categories"
      @save="saveSite"
      @close="showSiteModal = false"
    />
    <CategoryModal
      :visible="showCategoryModal"
      :category="editingCategory"
      @save="saveCategory"
      @delete="deleteCategory"
      @close="showCategoryModal = false"
    />
    <AppearanceModal
      v-model:dark-mode="isDarkMode"
      :visible="showAppearanceModal"
      @close="showAppearanceModal = false"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import HeroSearch from '../components/home/HeroSearch.vue'
import CareerRecommend from '../components/home/CareerRecommend.vue'
import PopularCategories from '../components/home/PopularCategories.vue'
import ToolCard from '../components/home/ToolCard.vue'
import FavoriteStack from '../components/home/FavoriteStack.vue'
import LoginModal from '../components/modals/LoginModal.vue'
import SiteFormModal from '../components/modals/SiteFormModal.vue'
import CategoryModal from '../components/modals/CategoryModal.vue'
import AppearanceModal from '../components/modals/AppearanceModal.vue'
import { navAPI } from '../utils/api'

const fallbackCategories = [
  { id: 'all', name: '全部工具' },
  { id: 5, name: 'AI 助手' },
  { id: 2, name: '编程开发' },
  { id: 4, name: '效率办公' },
  { id: 302, name: '设计素材' },
  { id: 403, name: '数据分析' }
]

const fallbackTools = [
  {
    id: 501,
    category_id: 5,
    name: 'ChatGPT',
    url: 'https://chat.openai.com',
    desc: 'AI 对话、写作、编程辅助工具',
    tags: ['AI写作', '编程', '学习'],
    audiences: ['学生', '程序员', '运营'],
    clicks: 760
  },
  {
    id: 514,
    category_id: 5,
    name: 'Cursor',
    url: 'https://www.cursor.com',
    desc: '面向开发者的 AI 代码编辑器',
    tags: ['编程', '代码', '文档'],
    audiences: ['程序员'],
    clicks: 530
  },
  {
    id: 202,
    category_id: 2,
    name: 'GitHub',
    url: 'https://github.com',
    desc: '代码托管、协作与开源项目平台',
    tags: ['代码', '文档', '部署'],
    audiences: ['程序员'],
    clicks: 980
  },
  {
    id: 3034,
    category_id: 302,
    name: 'Canva',
    url: 'https://www.canva.com',
    desc: '在线设计、PPT、海报和社媒素材制作',
    tags: ['设计', 'PPT', '素材'],
    audiences: ['学生', '设计师', '运营'],
    clicks: 640
  },
  {
    id: 412,
    category_id: 4,
    name: '百度翻译',
    url: 'https://fanyi.baidu.com',
    desc: '文本翻译、学习和跨语言写作辅助',
    tags: ['翻译', '学习', '文献'],
    audiences: ['学生', '运营'],
    clicks: 560
  },
  {
    id: 4035,
    category_id: 403,
    name: 'Tableau',
    url: 'https://www.tableau.com',
    desc: '数据可视化、看板分析和业务洞察',
    tags: ['数据', '看板', '分析'],
    audiences: ['运营', '产品经理'],
    clicks: 420
  },
  {
    id: 509,
    category_id: 5,
    name: 'Midjourney',
    url: 'https://www.midjourney.com',
    desc: 'AI 绘图与视觉创意生成工具',
    tags: ['绘图', '图片', '素材'],
    audiences: ['设计师', '运营'],
    clicks: 520
  },
  {
    id: 415,
    category_id: 4,
    name: 'iLovePDF',
    url: 'https://www.ilovepdf.com',
    desc: 'PDF 转换、压缩、合并和文档处理',
    tags: ['PDF', '论文', '办公'],
    audiences: ['学生', '运营'],
    clicks: 350
  },
  {
    id: 4044,
    category_id: 403,
    name: 'SEMrush',
    url: 'https://www.semrush.com',
    desc: 'SEO、热点分析和内容增长工具',
    tags: ['热点', '数据', '文案'],
    audiences: ['运营'],
    clicks: 330
  }
]

const careerKeywords = {
  学生: ['论文', 'PPT', '翻译', '学习', '文献'],
  程序员: ['编程', '代码', '接口', '部署', '文档'],
  设计师: ['设计', '绘图', '素材', '图片', '原型'],
  运营: ['文案', '数据', '热点', '短视频', '排版']
}

const articles = [
  { title: '如何用 AI 工具完成论文初稿整理', summary: '从资料检索、翻译到提纲生成的一套轻量流程。' },
  { title: '程序员常用 AI 工具组合', summary: '代码补全、接口调试、部署文档和协作平台怎么搭配。' },
  { title: '运营内容生产效率清单', summary: '热点、文案、排版、数据看板的实用入口。' }
]

const categories = ref([...fallbackCategories])
const websites = ref([...fallbackTools])
const searchQuery = ref('')
const activeCategoryId = ref('all')
const activeCareer = ref('')
const favoriteSiteIds = ref([])
const searchHistory = ref([])
const isDarkMode = ref(localStorage.getItem('theme') === 'dark')
const showLoginModal = ref(false)
const showSiteModal = ref(false)
const showCategoryModal = ref(false)
const showAppearanceModal = ref(false)
const editingSite = ref(null)
const editingCategory = ref(null)
const isLoggedIn = ref(localStorage.getItem('is_logged_in') === 'true')

const categoryOptions = computed(() => [
  { id: 'all', name: '全部工具' },
  { id: 'favorites', name: '我的收藏' },
  ...categories.value.filter((category) => category.id !== 'all')
])

const enrichedTools = computed(() => {
  const categoryMap = new Map(categories.value.map((category) => [category.id, category.name]))
  return websites.value.map((site) => ({
    ...site,
    categoryName: categoryMap.get(site.category_id) || 'AI 工具',
    tags: site.tags?.length ? site.tags : deriveTags(site, categoryMap.get(site.category_id)),
    audiences: site.audiences?.length ? site.audiences : deriveAudiences(site)
  }))
})

const filteredTools = computed(() => {
  let list = enrichedTools.value

  if (activeCategoryId.value === 'favorites') {
    list = list.filter((site) => favoriteSiteIds.value.includes(site.id))
  } else if (activeCategoryId.value !== 'all') {
    list = list.filter((site) => String(site.category_id) === String(activeCategoryId.value))
  }

  const keyword = searchQuery.value.trim().toLowerCase()
  if (keyword) {
    const careerTerms = careerKeywords[activeCareer.value] || []
    const terms = [keyword, ...careerTerms.map((term) => term.toLowerCase())]
    list = list.filter((site) => {
      const haystack = [
        site.name,
        site.desc,
        site.url,
        site.categoryName,
        ...(site.tags || []),
        ...(site.audiences || [])
      ].join(' ').toLowerCase()
      return terms.some((term) => haystack.includes(term))
    })
  }

  return list
})

const favoriteStackTools = computed(() => {
  const favorites = enrichedTools.value.filter((site) => favoriteSiteIds.value.includes(site.id))
  return (favorites.length ? favorites : enrichedTools.value).slice(0, 6)
})

const rankingTools = computed(() => [...enrichedTools.value].sort((a, b) => (b.clicks || 0) - (a.clicks || 0)).slice(0, 5))

const deriveTags = (site, categoryName = 'AI 工具') => {
  const text = `${site.name} ${site.desc || ''} ${categoryName}`
  const known = ['论文', 'PPT', '翻译', '编程', '代码', '部署', '设计', '绘图', '素材', '文案', '数据', '热点']
  const matched = known.filter((tag) => text.includes(tag))
  return (matched.length ? matched : [categoryName, '效率', 'AI']).slice(0, 3)
}

const deriveAudiences = (site) => {
  const text = `${site.name} ${site.desc || ''} ${(site.tags || []).join(' ')}`
  const audiences = Object.entries(careerKeywords)
    .filter(([, keywords]) => keywords.some((keyword) => text.includes(keyword)))
    .map(([career]) => career)
  return (audiences.length ? audiences : ['学生', '程序员', '运营']).slice(0, 3)
}

const loadNavData = async () => {
  try {
    const response = await navAPI.getNavData()
    const data = response.data?.data || response.data || {}
    if (Array.isArray(data.categories) && data.categories.length) {
      categories.value = [{ id: 'all', name: '全部工具' }, ...data.categories]
    }
    if (Array.isArray(data.websites) && data.websites.length) {
      websites.value = data.websites
    }
  } catch {
    categories.value = [...fallbackCategories]
    websites.value = [...fallbackTools]
  }
}

const selectCareer = (career) => {
  activeCareer.value = career
  searchQuery.value = career
  loadCareerRecommendations(career)
  document.querySelector('#tools')?.scrollIntoView({ behavior: 'smooth' })
}

const loadCareerRecommendations = (career) => {
  activeCategoryId.value = 'all'
  const firstKeyword = careerKeywords[career]?.[0]
  if (firstKeyword && !searchHistory.value.includes(firstKeyword)) {
    searchHistory.value = [firstKeyword, ...searchHistory.value].slice(0, 5)
  }
}

const selectCategory = (categoryId) => {
  activeCategoryId.value = categoryId
  if (categoryId !== 'favorites') activeCareer.value = ''
}

const showAllTools = () => {
  activeCategoryId.value = 'all'
  activeCareer.value = ''
  searchQuery.value = ''
  document.querySelector('#tools')?.scrollIntoView({ behavior: 'smooth' })
}

const showFavorites = () => {
  activeCategoryId.value = 'favorites'
  document.querySelector('#tools')?.scrollIntoView({ behavior: 'smooth' })
}

const doSearch = () => {
  const keyword = searchQuery.value.trim()
  if (!keyword) return
  searchHistory.value = [keyword, ...searchHistory.value.filter((item) => item !== keyword)].slice(0, 5)
  localStorage.setItem('search_history', JSON.stringify(searchHistory.value))
  document.querySelector('#tools')?.scrollIntoView({ behavior: 'smooth' })
}

const visitSite = async (site) => {
  if (!site?.url) return
  try {
    if (Number.isInteger(site.id)) await navAPI.recordClick(site.id)
  } catch {
    // Click analytics should never block navigation.
  }
  window.open(site.url, '_blank', 'noopener,noreferrer')
}

const toggleFavorite = (site) => {
  if (!site?.id) return
  const index = favoriteSiteIds.value.indexOf(site.id)
  if (index >= 0) favoriteSiteIds.value.splice(index, 1)
  else favoriteSiteIds.value.push(site.id)
  localStorage.setItem('favorite_site_ids', JSON.stringify(favoriteSiteIds.value))
}

const openSiteModal = (site = null) => {
  editingSite.value = site
  showSiteModal.value = true
}

const saveSite = (site) => {
  const normalized = {
    ...site,
    id: site.id || Date.now(),
    url: site.url.startsWith('http') ? site.url : `https://${site.url}`,
    category_id: site.category_id === 'all' ? categories.value.find((category) => category.id !== 'all')?.id : site.category_id
  }
  const index = websites.value.findIndex((item) => item.id === normalized.id)
  if (index >= 0) websites.value[index] = normalized
  else websites.value.unshift(normalized)
  showSiteModal.value = false
}

const saveCategory = (category) => {
  const normalized = { ...category, id: category.id || Date.now() }
  const index = categories.value.findIndex((item) => item.id === normalized.id)
  if (index >= 0) categories.value[index] = normalized
  else categories.value.push(normalized)
  showCategoryModal.value = false
}

const deleteCategory = (category) => {
  categories.value = categories.value.filter((item) => item.id !== category.id)
  if (activeCategoryId.value === category.id) activeCategoryId.value = 'all'
  showCategoryModal.value = false
}

watch(isDarkMode, (enabled) => {
  localStorage.setItem('theme', enabled ? 'dark' : 'light')
})

onMounted(() => {
  try {
    favoriteSiteIds.value = JSON.parse(localStorage.getItem('favorite_site_ids') || '[]')
    searchHistory.value = JSON.parse(localStorage.getItem('search_history') || '[]')
  } catch {
    favoriteSiteIds.value = []
    searchHistory.value = []
  }
  loadNavData()
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  color: #18212f;
  background: #f5f8fb;
}

.home-page.dark {
  color: #e5edf7;
  background: #111827;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
  border-bottom: 1px solid rgba(148, 163, 184, .24);
  padding: 14px min(6vw, 72px);
  background: rgba(245, 248, 251, .92);
  backdrop-filter: blur(18px);
}

.brand {
  color: inherit;
  font-weight: 800;
  text-decoration: none;
}

nav,
.topbar-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

nav a,
.topbar-actions a,
.topbar-actions button {
  border: 0;
  border-radius: 6px;
  padding: 9px 11px;
  color: inherit;
  background: transparent;
  font: inherit;
  text-decoration: none;
  cursor: pointer;
}

nav a:hover,
.topbar-actions a,
.topbar-actions button:hover {
  background: #e7eef7;
}

.tools-section {
  padding: 26px 0 10px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: end;
  padding: 0 min(6vw, 72px);
}

.section-heading p,
.info-band p,
.about-band p {
  margin: 0 0 8px;
  color: #1769aa;
  font-weight: 800;
}

.section-heading h2,
.info-band h2,
.about-band h2 {
  margin: 0;
}

.section-heading button {
  border: 0;
  border-radius: 6px;
  padding: 11px 16px;
  color: #fff;
  background: #18212f;
  cursor: pointer;
}

.tool-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  padding: 0 min(6vw, 72px);
}

.empty-state {
  margin: 22px min(6vw, 72px);
  color: #64748b;
}

.info-band {
  display: grid;
  grid-template-columns: minmax(220px, 320px) 1fr;
  gap: 24px;
  padding: 48px min(6vw, 72px);
  background: #fff;
}

.info-band ol {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.info-band li,
.article-list article {
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  padding: 14px 16px;
  background: #f8fbfe;
}

.info-band li {
  display: flex;
  justify-content: space-between;
  gap: 14px;
}

.article-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.article-list h3,
.article-list span {
  margin: 0;
}

.article-list span {
  display: block;
  margin-top: 8px;
  color: #64748b;
  line-height: 1.6;
}

.about-band {
  padding: 56px min(6vw, 72px) 84px;
}

.about-band h2 {
  max-width: 760px;
  font-size: 32px;
  line-height: 1.25;
}

.dark .topbar {
  background: rgba(17, 24, 39, .92);
}

.dark nav a:hover,
.dark .topbar-actions a,
.dark .topbar-actions button:hover {
  background: rgba(255, 255, 255, .1);
}

.dark .info-band,
.dark .info-band li,
.dark .article-list article {
  background: #172033;
  border-color: rgba(148, 163, 184, .24);
}

@media (max-width: 980px) {
  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }

  nav {
    flex-wrap: wrap;
  }

  .tool-grid,
  .article-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .topbar,
  .section-heading,
  .tool-grid,
  .info-band,
  .about-band {
    padding-inline: 20px;
  }

  .section-heading,
  .info-band {
    grid-template-columns: 1fr;
    display: grid;
  }

  .tool-grid,
  .article-list {
    grid-template-columns: 1fr;
  }
}
</style>
