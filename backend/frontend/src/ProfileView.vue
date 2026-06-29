<template>
  <div class="profile-page">
    <aside class="profile-sidebar">
      <button class="back-home" @click="router.push('/')">返回首页</button>

      <div class="profile-brief">
        <img :src="userInfo.avatar" class="brief-avatar" alt="用户头像" @error="useFallbackAvatar">
        <strong>{{ userInfo.username || '未命名用户' }}</strong>
        <span>{{ userInfo.email || '已登录账号' }}</span>
      </div>

      <nav class="profile-menu" aria-label="个人中心导航">
        <button :class="{ active: activeTab === 'homepage' }" @click="activeTab = 'homepage'">个人主页</button>
        <button :class="{ active: activeTab === 'settings' }" @click="activeTab = 'settings'">基础资料</button>
        <button :class="{ active: activeTab === 'security' }" @click="activeTab = 'security'">安全设置</button>
        <button :class="{ active: activeTab === 'content' }" @click="activeTab = 'content'">内容管理</button>
        <button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">互动足迹</button>
      </nav>

      <button class="logout-action" @click="handleLogout">退出当前账号</button>
    </aside>

    <main class="profile-main">
      <section v-if="activeTab === 'homepage'" class="profile-panel">
        <div class="panel-heading">
          <p>个人主页</p>
          <h1>{{ userInfo.username || '欢迎回来' }}</h1>
        </div>

        <div class="summary-grid">
          <div class="summary-card">
            <span>总阅读量</span>
            <strong>{{ profileStats.views || 0 }}</strong>
          </div>
          <div class="summary-card">
            <span>发布内容</span>
            <strong>{{ profileStats.posts || 0 }}</strong>
          </div>
          <div class="summary-card">
            <span>关注者</span>
            <strong>{{ profileStats.followers || 0 }}</strong>
          </div>
        </div>

        <div class="profile-card">
          <h2>效率标签</h2>
          <p>{{ userInfo.bio || '完善资料后，系统会更容易为你推荐适合的 AI 工具与网站。' }}</p>
          <div class="tag-row">
            <span>AI 工具</span>
            <span>职业推荐</span>
            <span>高效学习</span>
          </div>
        </div>
      </section>

      <section v-else-if="activeTab === 'settings'" class="profile-panel">
        <div class="panel-heading">
          <p>基础资料</p>
          <h1>编辑公开信息</h1>
        </div>

        <div class="form-card">
          <label>
            <span>名称</span>
            <input v-model="form.username" type="text" placeholder="请输入名称">
          </label>
          <label>
            <span>性别</span>
            <select v-model="form.gender">
              <option value="男">男</option>
              <option value="女">女</option>
              <option value="保密">保密</option>
            </select>
          </label>
          <label>
            <span>生日</span>
            <input v-model="form.birthday" type="date">
          </label>
          <label>
            <span>个性签名</span>
            <textarea v-model="form.bio" rows="4" placeholder="介绍一下你的学习或工作方向"></textarea>
          </label>

          <button class="primary-action" :disabled="isSaving" @click="saveProfile">
            {{ isSaving ? '保存中...' : '保存基础资料' }}
          </button>
          <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>
        </div>
      </section>

      <section v-else-if="activeTab === 'security'" class="profile-panel">
        <div class="panel-heading">
          <p>安全设置</p>
          <h1>账号与设备</h1>
        </div>

        <div class="list-card">
          <div class="list-row">
            <span>登录状态</span>
            <strong>已通过本地令牌登录</strong>
          </div>
          <div class="list-row">
            <span>绑定邮箱</span>
            <strong>{{ userInfo.email || '未绑定' }}</strong>
          </div>
          <div v-for="device in loginDevices" :key="device.id || device.name" class="list-row">
            <span>{{ device.name || '登录设备' }}</span>
            <strong>{{ device.location || '未知位置' }} {{ device.time || '' }}</strong>
          </div>
        </div>
      </section>

      <section v-else-if="activeTab === 'content'" class="profile-panel">
        <div class="panel-heading">
          <p>内容管理</p>
          <h1>我的发布</h1>
        </div>

        <div class="list-card">
          <div v-if="myContents.length === 0" class="empty-state">暂无发布的文章或项目</div>
          <button v-for="item in myContents" :key="item.id" class="content-row" @click="router.push(`/article/${item.id}`)">
            <span>{{ item.title }}</span>
            <small>{{ item.time || '刚刚' }} · {{ item.views || 0 }} 浏览</small>
          </button>
        </div>
      </section>

      <section v-else class="profile-panel">
        <div class="panel-heading">
          <p>互动足迹</p>
          <h1>最近访问</h1>
        </div>

        <div class="list-card">
          <div v-if="historyItems.length === 0" class="empty-state">暂无互动记录</div>
          <div v-for="(item, index) in historyItems" :key="index" class="list-row">
            <span>{{ item.action || '访问' }} {{ item.target_name || item.name || '网站' }}</span>
            <strong>{{ item.date || '' }} {{ item.time || '' }}</strong>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { userAPI } from './utils/api'

const router = useRouter()
const fallbackAvatar = 'https://api.dicebear.com/7.x/avataaars/svg?seed=fallback'

const activeTab = ref('homepage')
const isSaving = ref(false)
const statusMessage = ref('')
const profileStats = ref({ views: 0, followers: 0, posts: 0 })
const loginDevices = ref([])
const myContents = ref([])
const historyItems = ref([])

const userInfo = reactive({
  username: '',
  email: '',
  avatar: fallbackAvatar,
  gender: '保密',
  birthday: '',
  bio: ''
})

const form = reactive({
  username: '',
  gender: '保密',
  birthday: '',
  bio: ''
})

const syncForm = () => {
  form.username = userInfo.username || ''
  form.gender = userInfo.gender || '保密'
  form.birthday = userInfo.birthday || ''
  form.bio = userInfo.bio || ''
}

const loadLocalUser = () => {
  const saved = localStorage.getItem('user_info')
  if (!saved) {
    syncForm()
    return
  }

  try {
    Object.assign(userInfo, JSON.parse(saved))
    userInfo.avatar = userInfo.avatar || fallbackAvatar
  } catch (error) {
    console.warn('[Profile] 无法解析本地用户信息:', error)
  }
  syncForm()
}

const loadRemoteProfile = async () => {
  if (!userInfo.username) return

  try {
    const [statsRes, devicesRes, historyRes, contentsRes] = await Promise.allSettled([
      userAPI.getStats(userInfo.username),
      userAPI.getDevices(),
      userAPI.getHistory(),
      userAPI.getContents('pending')
    ])

    if (statsRes.status === 'fulfilled') {
      profileStats.value = statsRes.value.data?.data || statsRes.value.data || profileStats.value
    }
    if (devicesRes.status === 'fulfilled') {
      loginDevices.value = devicesRes.value.data?.data || devicesRes.value.data || []
    }
    if (historyRes.status === 'fulfilled') {
      historyItems.value = historyRes.value.data?.data || historyRes.value.data || []
    }
    if (contentsRes.status === 'fulfilled') {
      myContents.value = contentsRes.value.data?.data || contentsRes.value.data || []
    }
  } catch (error) {
    console.warn('[Profile] 加载远程资料失败:', error)
  }
}

const saveProfile = async () => {
  isSaving.value = true
  statusMessage.value = ''

  try {
    const payload = {
      username: form.username,
      gender: form.gender,
      birthday: form.birthday,
      bio: form.bio
    }
    await userAPI.updateProfile(payload)
    Object.assign(userInfo, payload)
    localStorage.setItem('user_info', JSON.stringify(userInfo))
    statusMessage.value = '资料已保存'
  } catch (error) {
    console.error('[Profile] 保存资料失败:', error)
    statusMessage.value = '保存失败，请稍后重试'
  } finally {
    isSaving.value = false
  }
}

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_info')
  localStorage.removeItem('is_logged_in')
  router.push('/login')
}

const useFallbackAvatar = (event) => {
  event.target.src = fallbackAvatar
}

onMounted(() => {
  loadLocalUser()
  loadRemoteProfile()
})
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px 1fr;
  background:
    radial-gradient(circle at 8% 10%, rgba(239, 114, 92, 0.12), transparent 280px),
    linear-gradient(135deg, #f8fafc, #eef2f7);
  color: #223044;
}

.profile-sidebar {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 28px;
  border-right: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.82);
}

.back-home,
.logout-action,
.profile-menu button,
.primary-action,
.content-row {
  font: inherit;
  cursor: pointer;
}

.back-home {
  width: max-content;
  padding: 0;
  border: 0;
  background: transparent;
  color: #ef725c;
  font-weight: 800;
}

.profile-brief {
  display: grid;
  gap: 8px;
}

.brief-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  border: 3px solid #fff;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.12);
  object-fit: cover;
}

.profile-brief strong {
  color: #1f2937;
  font-size: 20px;
}

.profile-brief span,
.panel-heading p,
.summary-card span,
.list-row span,
.content-row small,
.status-message {
  color: #64748b;
}

.profile-menu {
  display: grid;
  gap: 10px;
}

.profile-menu button {
  min-height: 42px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #475569;
  text-align: left;
  font-weight: 760;
}

.profile-menu button:hover,
.profile-menu button.active {
  border-color: #f5c3ba;
  background: #fff3f0;
  color: #ef725c;
}

.logout-action {
  margin-top: auto;
  min-height: 42px;
  border: 0;
  border-radius: 8px;
  background: #1f2937;
  color: #fff;
  font-weight: 800;
}

.profile-main {
  min-width: 0;
  padding: 48px;
}

.profile-panel {
  max-width: 980px;
  display: grid;
  gap: 24px;
}

.panel-heading p {
  margin: 0 0 8px;
  font-weight: 800;
}

.panel-heading h1 {
  margin: 0;
  color: #1f2937;
  font-size: clamp(32px, 4vw, 54px);
  line-height: 1.05;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.summary-card,
.profile-card,
.form-card,
.list-card {
  border: 1px solid rgba(203, 213, 225, 0.7);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 20px 54px rgba(15, 23, 42, 0.07);
}

.summary-card {
  display: grid;
  gap: 8px;
  padding: 22px;
}

.summary-card strong {
  color: #1f2937;
  font-size: 34px;
}

.profile-card,
.form-card,
.list-card {
  padding: 26px;
}

.profile-card h2 {
  margin: 0 0 10px;
  color: #1f2937;
}

.profile-card p {
  margin: 0 0 18px;
  color: #64748b;
  line-height: 1.7;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag-row span {
  padding: 7px 11px;
  border-radius: 999px;
  background: #f8fafc;
  color: #ef725c;
  font-size: 12px;
  font-weight: 800;
}

.form-card {
  display: grid;
  gap: 18px;
}

.form-card label {
  display: grid;
  gap: 8px;
  color: #334155;
  font-weight: 780;
}

.form-card input,
.form-card select,
.form-card textarea {
  width: 100%;
  min-height: 42px;
  padding: 10px 12px;
  border: 1px solid #d8dde3;
  border-radius: 8px;
  background: #fff;
  color: #1f2937;
  font: inherit;
}

.form-card textarea {
  resize: vertical;
}

.primary-action {
  width: max-content;
  min-height: 42px;
  padding: 0 18px;
  border: 0;
  border-radius: 8px;
  background: #ef725c;
  color: #fff;
  font-weight: 850;
}

.primary-action:disabled {
  opacity: 0.7;
  cursor: wait;
}

.status-message {
  margin: 0;
}

.list-card {
  display: grid;
  gap: 0;
}

.list-row,
.content-row {
  min-height: 58px;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid #e2e8f0;
}

.list-row:last-child,
.content-row:last-child {
  border-bottom: 0;
}

.list-row strong {
  color: #334155;
  font-size: 14px;
}

.content-row {
  width: 100%;
  border-right: 0;
  border-left: 0;
  border-top: 0;
  background: transparent;
  text-align: left;
}

.content-row span {
  color: #1f2937;
  font-weight: 800;
}

.empty-state {
  padding: 32px 0;
  color: #94a3b8;
  text-align: center;
}

@media (max-width: 860px) {
  .profile-page {
    grid-template-columns: 1fr;
  }

  .profile-sidebar {
    min-height: 0;
    border-right: 0;
    border-bottom: 1px solid rgba(148, 163, 184, 0.28);
  }

  .profile-main {
    padding: 28px 18px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .list-row,
  .content-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
