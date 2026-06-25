<template>
  <main class="admin-page">
    <header class="admin-header">
      <div>
        <p>智汇导航</p>
        <h1>管理后台</h1>
      </div>
      <button @click="$router.push('/')">返回前台</button>
    </header>

    <section class="overview-grid">
      <article v-for="card in overviewCards" :key="card.key">
        <span>{{ card.label }}</span>
        <strong>{{ overview[card.key] || 0 }}</strong>
      </article>
    </section>

    <section class="admin-tabs">
      <button v-for="tab in tabs" :key="tab.key" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
        {{ tab.label }}
      </button>
    </section>

    <section v-if="activeTab === 'sites'" class="admin-panel">
      <form class="admin-form sites-form" @submit.prevent="saveSite">
        <input v-model="siteForm.name" placeholder="网站名称" required />
        <input v-model="siteForm.url" placeholder="https://example.com" required />
        <select v-model="siteForm.category">
          <option v-for="category in categories" :key="category.id" :value="category.id">{{ category.name }}</option>
        </select>
        <input v-model="siteForm.tags" placeholder="标签，如 ai,learning,design" />
        <input v-model="siteForm.description" class="wide" placeholder="用途描述" />
        <div class="form-actions">
          <button>{{ editingSiteId ? '保存修改' : '新增网站' }}</button>
          <button v-if="editingSiteId" type="button" class="ghost" @click="resetSiteForm">取消</button>
        </div>
      </form>
      <div class="admin-list">
        <article v-for="site in sites" :key="site.id">
          <div>
            <strong>{{ site.name }}</strong>
            <span>{{ site.description || site.url }}</span>
          </div>
          <div class="row-actions">
            <button class="ghost" @click="editSite(site)">编辑</button>
            <button class="danger" @click="deleteSite(site.id)">删除</button>
          </div>
        </article>
        <p v-if="sites.length === 0" class="empty">暂无网站数据。</p>
      </div>
    </section>

    <section v-else-if="activeTab === 'categories'" class="admin-panel">
      <form class="admin-form simple-form" @submit.prevent="createCategory">
        <input v-model="categoryForm.name" placeholder="分类名称" required />
        <input v-model="categoryForm.profession_type" placeholder="profession_type" />
        <button>新增分类</button>
      </form>
      <div class="admin-list">
        <article v-for="category in categories" :key="category.id">
          <div>
            <strong>{{ category.name }}</strong>
            <span>{{ category.profession_type || 'general' }}</span>
          </div>
          <button class="danger" @click="deleteCategory(category.id)">删除</button>
        </article>
        <p v-if="categories.length === 0" class="empty">暂无分类数据。</p>
      </div>
    </section>

    <section v-else-if="activeTab === 'tags'" class="admin-panel">
      <form class="admin-form simple-form" @submit.prevent="createTag">
        <input v-model="tagForm.name" placeholder="标签名称" required />
        <select v-model="tagForm.type">
          <option value="interest">兴趣</option>
          <option value="occupation">职业</option>
        </select>
        <button>新增标签</button>
      </form>
      <div class="admin-list">
        <article v-for="tag in tags" :key="tag.id">
          <div>
            <strong>{{ tag.name }}</strong>
            <span>{{ tag.slug }} · {{ tag.type }}</span>
          </div>
          <button class="danger" @click="deleteTag(tag.id)">删除</button>
        </article>
        <p v-if="tags.length === 0" class="empty">暂无标签数据。</p>
      </div>
    </section>

    <section v-else-if="activeTab === 'users'" class="admin-panel">
      <div class="admin-list">
        <article v-for="user in users" :key="user.id">
          <div>
            <strong>{{ user.username }}</strong>
            <span>{{ user.email || '未绑定邮箱' }} · 注册于 {{ user.created_at || '-' }}</span>
          </div>
          <span class="pill">ID {{ user.id }}</span>
        </article>
        <p v-if="users.length === 0" class="empty">暂无用户数据。</p>
      </div>
    </section>

    <section v-else-if="activeTab === 'comments'" class="admin-panel">
      <div class="admin-list">
        <article v-for="comment in comments" :key="comment.id" class="stacked">
          <div class="list-head">
            <div>
              <strong>{{ comment.website_name || '未知网站' }}</strong>
              <span>{{ comment.username }} · {{ comment.created_at }}</span>
            </div>
            <span class="pill" :class="comment.status">{{ statusText(comment.status) }}</span>
          </div>
          <p>{{ comment.content }}</p>
          <div class="row-actions">
            <button class="ghost" @click="reviewComment(comment.id, 'approved')">通过</button>
            <button class="ghost" @click="reviewComment(comment.id, 'pending')">待审</button>
            <button class="danger" @click="reviewComment(comment.id, 'rejected')">拒绝</button>
            <button class="danger" @click="deleteComment(comment.id)">删除</button>
          </div>
        </article>
        <p v-if="comments.length === 0" class="empty">暂无评论数据。</p>
      </div>
    </section>

    <section v-else-if="activeTab === 'reports'" class="admin-panel">
      <div class="admin-list">
        <article v-for="report in reports" :key="report.id" class="stacked">
          <div class="list-head">
            <div>
              <strong>{{ report.target_name || report.target_type + ' #' + report.target_id }}</strong>
              <span>{{ report.created_at }} · 用户 ID {{ report.user_id || '-' }}</span>
            </div>
            <span class="pill" :class="report.status">{{ statusText(report.status) }}</span>
          </div>
          <p>{{ report.reason }}</p>
          <div class="row-actions">
            <button class="ghost" @click="updateReport(report.id, 'pending')">待处理</button>
            <button class="ghost" @click="updateReport(report.id, 'processed')">已处理</button>
            <button class="danger" @click="updateReport(report.id, 'rejected')">驳回</button>
          </div>
        </article>
        <p v-if="reports.length === 0" class="empty">暂无举报数据。</p>
      </div>
    </section>

    <section v-else-if="activeTab === 'dmca'" class="admin-panel">
      <div class="admin-list">
        <article v-for="item in dmcaItems" :key="item.id" class="stacked">
          <div class="list-head">
            <div>
              <strong>{{ item.name || 'DMCA 投诉' }}</strong>
              <span>{{ item.email || '-' }} · {{ item.created_at }}</span>
            </div>
            <span class="pill" :class="item.status">{{ statusText(item.status) }}</span>
          </div>
          <span>{{ item.url }}</span>
          <p>{{ item.description }}</p>
          <div class="row-actions">
            <button class="ghost" @click="updateDmca(item.id, 'pending')">待处理</button>
            <button class="ghost" @click="updateDmca(item.id, 'processed')">已处理</button>
            <button class="danger" @click="updateDmca(item.id, 'rejected')">驳回</button>
          </div>
        </article>
        <p v-if="dmcaItems.length === 0" class="empty">暂无 DMCA 投诉。</p>
      </div>
    </section>

    <p class="message">{{ message }}</p>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { adminAPI } from '@/utils/api'

const tabs = [
  { key: 'sites', label: '网站管理' },
  { key: 'categories', label: '分类管理' },
  { key: 'tags', label: '标签管理' },
  { key: 'users', label: '用户管理' },
  { key: 'comments', label: '评论管理' },
  { key: 'reports', label: '举报管理' },
  { key: 'dmca', label: 'DMCA' }
]
const overviewCards = [
  { key: 'users', label: '用户数' },
  { key: 'websites', label: '网站数' },
  { key: 'favorites', label: '收藏数' },
  { key: 'comments', label: '评论数' },
  { key: 'today_visits', label: '今日访问' },
  { key: 'reports', label: '待处理举报' },
  { key: 'dmca', label: '待处理 DMCA' }
]

const activeTab = ref('sites')
const sites = ref([])
const categories = ref([])
const tags = ref([])
const users = ref([])
const comments = ref([])
const reports = ref([])
const dmcaItems = ref([])
const message = ref('')
const editingSiteId = ref(null)
const overview = reactive({})
const siteForm = reactive({ name: '', url: '', category: '', description: '', tags: '' })
const categoryForm = reactive({ name: '', profession_type: 'general' })
const tagForm = reactive({ name: '', type: 'interest' })

const loadOverview = async () => {
  const res = await adminAPI.getOverview()
  Object.assign(overview, res.data?.data || {})
}

const loadSites = async () => {
  const res = await adminAPI.getWebsites({ per_page: 100 })
  sites.value = res.data?.data?.items || []
}

const loadCategories = async () => {
  const res = await adminAPI.getCategories()
  categories.value = res.data?.data || []
  if (!siteForm.category && categories.value[0]) siteForm.category = categories.value[0].id
}

const loadTags = async () => {
  const res = await adminAPI.getTags()
  tags.value = res.data?.data || []
}

const loadUsers = async () => {
  const res = await adminAPI.getUsers(1, 100)
  users.value = res.data?.data?.users || []
}

const loadComments = async () => {
  const res = await adminAPI.getComments()
  comments.value = res.data?.data || []
}

const loadReports = async () => {
  const res = await adminAPI.getReports()
  reports.value = res.data?.data || []
}

const loadDmca = async () => {
  const res = await adminAPI.getDmcaList()
  dmcaItems.value = res.data?.data || []
}

const loadAll = async () => {
  try {
    await Promise.all([
      loadOverview(),
      loadSites(),
      loadCategories(),
      loadTags(),
      loadUsers(),
      loadComments(),
      loadReports(),
      loadDmca()
    ])
  } catch (error) {
    message.value = error.response?.data?.msg || '后台数据加载失败'
  }
}

const resetSiteForm = () => {
  editingSiteId.value = null
  Object.assign(siteForm, { name: '', url: '', category: siteForm.category || categories.value[0]?.id || '', description: '', tags: '' })
}

const saveSite = async () => {
  try {
    if (editingSiteId.value) {
      await adminAPI.updateWebsite(editingSiteId.value, siteForm)
      message.value = '网站已更新'
    } else {
      await adminAPI.createWebsite(siteForm)
      message.value = '网站已创建'
    }
    resetSiteForm()
    await Promise.all([loadSites(), loadOverview()])
  } catch (error) {
    message.value = error.response?.data?.msg || '网站保存失败'
  }
}

const editSite = (site) => {
  editingSiteId.value = site.id
  Object.assign(siteForm, {
    name: site.name,
    url: site.url,
    category: site.category_id,
    description: site.description || '',
    tags: (site.tags || []).join(',')
  })
}

const deleteSite = async (id) => {
  await adminAPI.deleteWebsite(id)
  message.value = '网站已删除'
  await Promise.all([loadSites(), loadOverview()])
}

const createCategory = async () => {
  await adminAPI.createCategory(categoryForm)
  Object.assign(categoryForm, { name: '', profession_type: 'general' })
  message.value = '分类已创建'
  await loadCategories()
}

const deleteCategory = async (id) => {
  await adminAPI.deleteCategory(id)
  message.value = '分类已删除'
  await loadCategories()
}

const createTag = async () => {
  await adminAPI.createTag(tagForm)
  Object.assign(tagForm, { name: '', type: 'interest' })
  message.value = '标签已创建'
  await loadTags()
}

const deleteTag = async (id) => {
  await adminAPI.deleteTag(id)
  message.value = '标签已删除'
  await loadTags()
}

const reviewComment = async (id, status) => {
  await adminAPI.reviewComment(id, status)
  message.value = '评论状态已更新'
  await Promise.all([loadComments(), loadOverview()])
}

const deleteComment = async (id) => {
  await adminAPI.deleteComment(id)
  message.value = '评论已删除'
  await Promise.all([loadComments(), loadOverview()])
}

const updateReport = async (id, status) => {
  await adminAPI.updateReportStatus(id, status)
  message.value = '举报状态已更新'
  await Promise.all([loadReports(), loadOverview()])
}

const updateDmca = async (id, status) => {
  await adminAPI.updateDmcaStatus(id, status)
  message.value = 'DMCA 状态已更新'
  await Promise.all([loadDmca(), loadOverview()])
}

const statusText = (status) => {
  const map = {
    approved: '已通过',
    pending: '待处理',
    rejected: '已驳回',
    processed: '已处理'
  }
  return map[status] || status || '未知'
}

watch(activeTab, () => { message.value = '' })
onMounted(loadAll)
</script>

<style scoped>
.admin-page { min-height: 100vh; background: #f6f7fb; color: #172033; padding: 28px; }
.admin-header, .overview-grid, .admin-tabs, .admin-panel, .message { max-width: 1180px; margin-left: auto; margin-right: auto; }
.admin-header { margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.admin-header p { margin: 0 0 6px; color: #64748b; font-size: 13px; }
h1 { margin: 0; font-size: 30px; letter-spacing: 0; }
button { border: 0; border-radius: 6px; background: #111827; color: #fff; min-height: 38px; padding: 0 14px; cursor: pointer; font-weight: 700; }
.overview-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }
.overview-grid article { background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 14px; }
.overview-grid span { color: #64748b; font-size: 12px; }
.overview-grid strong { display: block; margin-top: 8px; font-size: 22px; }
.admin-tabs { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.admin-tabs button, .ghost { background: #e9edf5; color: #172033; }
.admin-tabs button.active { background: #111827; color: #fff; }
.admin-panel { background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 18px; }
.admin-form { display: grid; gap: 10px; margin-bottom: 16px; }
.simple-form { grid-template-columns: 1fr 1fr 120px; }
.sites-form { grid-template-columns: 1fr 1.4fr 160px 1fr; }
.wide { grid-column: span 3; }
.form-actions, .row-actions { display: flex; gap: 8px; flex-wrap: wrap; }
input, select { height: 38px; border: 1px solid #dbe1ec; border-radius: 6px; padding: 0 10px; min-width: 0; }
.admin-list { display: grid; gap: 10px; }
.admin-list > article { display: flex; justify-content: space-between; gap: 12px; align-items: center; border: 1px solid #eef1f6; border-radius: 8px; padding: 12px; }
.admin-list > article.stacked { display: grid; align-items: stretch; }
.list-head { display: flex; justify-content: space-between; gap: 12px; align-items: start; }
strong, span { display: block; }
span { color: #64748b; font-size: 13px; word-break: break-all; }
p { margin: 0; color: #334155; line-height: 1.6; word-break: break-word; }
.danger { background: #fee2e2; color: #991b1b; }
.pill { border: 1px solid #dbe1ec; border-radius: 999px; padding: 5px 10px; color: #475569; white-space: nowrap; }
.pill.approved, .pill.processed { border-color: #bbf7d0; color: #166534; background: #f0fdf4; }
.pill.pending { border-color: #fde68a; color: #92400e; background: #fffbeb; }
.pill.rejected { border-color: #fecaca; color: #991b1b; background: #fef2f2; }
.message { min-height: 22px; color: #475569; }
.empty { color: #64748b; }
@media (max-width: 960px) {
  .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sites-form, .simple-form { grid-template-columns: 1fr; }
  .wide { grid-column: auto; }
}
@media (max-width: 640px) {
  .admin-page { padding: 18px; }
  .admin-header, .admin-list > article, .list-head { align-items: stretch; flex-direction: column; }
  .overview-grid { grid-template-columns: 1fr; }
  .row-actions, .form-actions { flex-direction: column; }
}
</style>
