<template>
  <main class="profile-page">
    <section class="profile-shell">
      <header class="profile-header">
        <div>
          <p>个人中心</p>
          <h1>{{ profile.username || '我的账号' }}</h1>
        </div>
        <div class="header-actions">
          <button class="ghost" @click="$router.push('/')">返回首页</button>
          <button @click="logout">退出登录</button>
        </div>
      </header>

      <section class="summary-grid">
        <article>
          <span>邮箱</span>
          <strong>{{ profile.email || '未绑定' }}</strong>
        </article>
        <article>
          <span>收藏网站</span>
          <strong>{{ profile.favorite_count || 0 }}</strong>
        </article>
        <article>
          <span>评论记录</span>
          <strong>{{ profile.comment_count || 0 }}</strong>
        </article>
        <article>
          <span>问卷状态</span>
          <strong>{{ profile.has_survey ? '已完成' : '未完成' }}</strong>
        </article>
      </section>

      <section class="profile-card">
        <div class="section-title">
          <div>
            <p>需求画像</p>
            <h2>职业与兴趣标签</h2>
          </div>
          <button class="ghost" @click="$router.push('/questionnaire')">重新填写问卷</button>
        </div>
        <div class="tag-list" v-if="profile.tags?.length">
          <span v-for="tag in profile.tags" :key="tag">{{ tag }}</span>
        </div>
        <p v-else class="empty">还没有问卷标签，完成问卷后会用于个性化推荐。</p>
      </section>

      <section class="two-column">
        <article class="profile-card">
          <div class="section-title compact">
            <div>
              <p>浏览足迹</p>
              <h2>最近访问</h2>
            </div>
          </div>
          <div class="activity-list" v-if="activity.behaviors?.length">
            <button v-for="item in activity.behaviors" :key="item.id" @click="openSite(item.website_id)">
              <span>{{ item.website_name || '网站访问' }}</span>
              <small>{{ item.created_at || '-' }}</small>
            </button>
          </div>
          <p v-else class="empty">暂无浏览记录。</p>
        </article>

        <article class="profile-card">
          <div class="section-title compact">
            <div>
              <p>互动记录</p>
              <h2>我的评论</h2>
            </div>
          </div>
          <div class="comment-list" v-if="activity.comments?.length">
            <article v-for="comment in activity.comments" :key="comment.id">
              <strong>{{ comment.website_name || '网站' }}</strong>
              <p>{{ comment.content }}</p>
              <span>{{ statusText(comment.status) }} · {{ comment.created_at || '-' }}</span>
            </article>
          </div>
          <p v-else class="empty">暂无评论记录。</p>
        </article>
      </section>

      <p class="message">{{ message }}</p>
    </section>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { clearAuthSession, userAPI } from '@/utils/api'

const router = useRouter()
const message = ref('')
const profile = reactive({
  username: '',
  email: '',
  has_survey: false,
  tags: [],
  favorite_count: 0,
  comment_count: 0
})
const activity = reactive({
  behaviors: [],
  comments: []
})

const loadProfile = async () => {
  try {
    const [profileRes, activityRes] = await Promise.all([
      userAPI.getProfile(),
      userAPI.getActivity()
    ])
    Object.assign(profile, profileRes.data?.data || {})
    Object.assign(activity, activityRes.data?.data || { behaviors: [], comments: [] })
  } catch (error) {
    message.value = error.response?.data?.msg || '个人中心加载失败，请重新登录'
  }
}

const openSite = (id) => {
  if (id) router.push('/site/' + id)
}

const logout = () => {
  clearAuthSession()
  router.push('/login')
}

const statusText = (status) => {
  const map = { approved: '已通过', pending: '待审核', rejected: '已拒绝' }
  return map[status] || status || '未知'
}

onMounted(loadProfile)
</script>

<style scoped>
.profile-page { min-height: 100vh; background: #f6f7fb; color: #172033; padding: 28px; }
.profile-shell { width: min(1120px, 100%); margin: 0 auto; }
.profile-header { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 18px; }
.profile-header p, .section-title p { margin: 0 0 6px; color: #64748b; font-size: 13px; }
h1, h2 { margin: 0; letter-spacing: 0; }
h1 { font-size: 32px; }
h2 { font-size: 20px; }
button { border: 0; border-radius: 6px; min-height: 40px; padding: 0 14px; background: #111827; color: #fff; font-weight: 700; cursor: pointer; }
.ghost { background: #e9edf5; color: #172033; }
.header-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px; }
.summary-grid article, .profile-card { background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 18px; }
.summary-grid span { color: #64748b; font-size: 13px; }
.summary-grid strong { display: block; margin-top: 8px; font-size: 24px; word-break: break-word; }
.section-title { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 14px; }
.section-title.compact { margin-bottom: 12px; }
.tag-list { display: flex; gap: 8px; flex-wrap: wrap; }
.tag-list span { border: 1px solid #dbe1ec; border-radius: 999px; padding: 7px 11px; color: #475569; font-size: 13px; }
.two-column { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 14px; }
.activity-list { display: grid; gap: 10px; }
.activity-list button { display: flex; justify-content: space-between; gap: 12px; align-items: center; background: #f8fafc; color: #172033; border: 1px solid #eef1f6; text-align: left; }
small { color: #64748b; }
.comment-list { display: grid; gap: 10px; }
.comment-list article { border: 1px solid #eef1f6; border-radius: 8px; padding: 12px; }
.comment-list p { margin: 8px 0; color: #334155; line-height: 1.6; }
.comment-list span, .empty, .message { color: #64748b; }
.empty { margin: 0; }
.message { min-height: 22px; margin-top: 14px; }
@media (max-width: 760px) {
  .profile-page { padding: 18px; }
  .profile-header, .section-title, .activity-list button { align-items: stretch; flex-direction: column; }
  .summary-grid, .two-column { grid-template-columns: 1fr; }
  .header-actions { flex-direction: column; }
}
</style>
