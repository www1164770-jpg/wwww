<template>
  <div class="profile-page">
    <ProfileSidebar
      v-model:active-tab="activeTab"
      :user-info="userInfo"
      @back-home="router.push('/')"
      @logout="handleLogout"
    />

    <main class="profile-main">
      <section v-if="activeTab === 'homepage'" class="panel">
        <div class="heading">
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

      <ProfileBasic
        v-else-if="activeTab === 'basic'"
        :form="form"
        @update:field="updateFormField"
        @save="saveProfile"
      />

      <ProfileSecurity
        v-else-if="activeTab === 'security'"
        :user-info="userInfo"
        :devices="loginDevices"
      />

      <ProfilePrivacy
        v-else-if="activeTab === 'privacy'"
        :settings="privacySettings"
        @update:setting="updatePrivacySetting"
      />

      <ProfileContent
        v-else-if="activeTab === 'content'"
        mode="content"
        :items="myContents"
        @open-item="openContent"
      />

      <ProfileContent
        v-else
        mode="history"
        :items="historyItems"
      />

      <p v-if="statusMessage" class="status-message">{{ statusMessage }}</p>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { userAPI } from '../utils/api'
import ProfileSidebar from '../components/profile/ProfileSidebar.vue'
import ProfileBasic from '../components/profile/ProfileBasic.vue'
import ProfileSecurity from '../components/profile/ProfileSecurity.vue'
import ProfilePrivacy from '../components/profile/ProfilePrivacy.vue'
import ProfileContent from '../components/profile/ProfileContent.vue'

const router = useRouter()
const fallbackAvatar = 'https://api.dicebear.com/7.x/avataaars/svg?seed=fallback'

const activeTab = ref('homepage')
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

const privacySettings = reactive({
  publicFavorites: true,
  hideFootprint: false,
  personalized: true
})

const syncForm = () => {
  form.username = userInfo.username || ''
  form.gender = userInfo.gender || '保密'
  form.birthday = userInfo.birthday || ''
  form.bio = userInfo.bio || ''
}

const loadLocalUser = () => {
  const saved = localStorage.getItem('user_info')
  if (saved) {
    try {
      Object.assign(userInfo, JSON.parse(saved))
    } catch {
      statusMessage.value = '本地用户信息读取失败，已使用默认资料。'
    }
  }
  if (!userInfo.avatar) userInfo.avatar = fallbackAvatar
  syncForm()
}

const loadProfileData = async () => {
  try {
    const [stats, devices, contents, history] = await Promise.allSettled([
      userAPI.getStats(userInfo.username || ''),
      userAPI.getDevices(),
      userAPI.getContents('all'),
      userAPI.getHistory()
    ])

    if (stats.status === 'fulfilled') profileStats.value = stats.value.data?.data || stats.value.data || profileStats.value
    if (devices.status === 'fulfilled') loginDevices.value = devices.value.data?.data || devices.value.data || []
    if (contents.status === 'fulfilled') myContents.value = contents.value.data?.data || contents.value.data || []
    if (history.status === 'fulfilled') historyItems.value = history.value.data?.data || history.value.data || []
  } catch {
    statusMessage.value = '部分个人中心数据暂时不可用。'
  }
}

const updateFormField = (field, value) => {
  form[field] = value
}

const updatePrivacySetting = (field, value) => {
  privacySettings[field] = value
  localStorage.setItem('privacy_settings', JSON.stringify(privacySettings))
}

const saveProfile = async () => {
  statusMessage.value = ''
  Object.assign(userInfo, form)
  localStorage.setItem('user_info', JSON.stringify(userInfo))

  try {
    await userAPI.updateProfile({ ...form })
    statusMessage.value = '基础资料已保存。'
  } catch {
    statusMessage.value = '已保存到本地，云端同步稍后重试。'
  }
}

const openContent = (item) => {
  if (item?.id) router.push(`/article/${item.id}`)
}

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('is_logged_in')
  localStorage.removeItem('user_info')
  router.push('/login')
}

onMounted(() => {
  loadLocalUser()
  const privacy = localStorage.getItem('privacy_settings')
  if (privacy) {
    try {
      Object.assign(privacySettings, JSON.parse(privacy))
    } catch {
      localStorage.removeItem('privacy_settings')
    }
  }
  loadProfileData()
})
</script>

<style scoped>
.profile-page {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 100vh;
  color: #18212f;
  background: #f5f8fb;
}

.profile-main {
  display: grid;
  align-content: start;
  gap: 20px;
  padding: 36px;
}

.panel {
  display: grid;
  gap: 20px;
}

.heading p,
.heading h1 {
  margin: 0;
}

.heading p {
  color: #1769aa;
  font-weight: 700;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  max-width: 760px;
}

.summary-card,
.profile-card {
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  padding: 20px;
  background: #fff;
}

.summary-card {
  display: grid;
  gap: 8px;
}

.summary-card span,
.profile-card p {
  color: #64748b;
}

.summary-card strong {
  font-size: 32px;
}

.profile-card {
  max-width: 760px;
}

.profile-card h2,
.profile-card p {
  margin: 0;
}

.profile-card p {
  margin-top: 10px;
  line-height: 1.7;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.tag-row span {
  border-radius: 999px;
  padding: 6px 10px;
  color: #1769aa;
  background: #e9f4fc;
}

.status-message {
  margin: 0;
  color: #1769aa;
}

@media (max-width: 820px) {
  .profile-page {
    grid-template-columns: 1fr;
  }

  .profile-main {
    padding: 24px 20px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
