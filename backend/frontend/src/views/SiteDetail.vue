<template>
  <main class="detail-page">
    <section v-if="site" class="detail-panel">
      <RouterLink to="/">返回首页</RouterLink>
      <div class="head">
        <img :src="site.logo_url || fallbackLogo(site)" :alt="site.name" />
        <div>
          <h1>{{ site.name }}</h1>
          <p>{{ site.description || site.category_name || '系统收录网站' }}</p>
        </div>
      </div>

      <div class="meta">
        <span>分类：{{ site.category_name || site.category_id }}</span>
        <span>点击：{{ site.clicks || 0 }}</span>
        <span v-if="site.match_percent">匹配度：{{ site.match_percent }}%</span>
      </div>

      <div class="tags" v-if="site.tags?.length">
        <span v-for="tag in site.tags" :key="tag">{{ tag }}</span>
      </div>

      <section class="rating-box">
        <div>
          <strong>{{ site.avg_rating ? site.avg_rating + ' / 5' : '暂无评分' }}</strong>
          <span>{{ site.rating_count || 0 }} 人评分</span>
        </div>
        <div class="stars">
          <button v-for="score in 5" :key="score" type="button" :class="{ active: score <= myRating }" @click="rate(score)">
            ★
          </button>
        </div>
      </section>

      <footer>
        <button @click="visit">访问网站</button>
        <button class="ghost" @click="favorite">{{ favText }}</button>
        <button class="ghost" @click="showReport = !showReport">举报网站</button>
      </footer>

      <section v-if="showReport" class="report-box">
        <h2>举报网站</h2>
        <textarea v-model="reportReason" placeholder="请描述侵权、失效、违规或其它问题" maxlength="500"></textarea>
        <div class="report-actions">
          <button type="button" @click="submitReport" :disabled="reporting">{{ reporting ? '提交中' : '提交举报' }}</button>
          <button type="button" class="ghost" @click="showReport = false">取消</button>
        </div>
      </section>

      <section class="comments">
        <h2>用户评论</h2>
        <form @submit.prevent="postComment">
          <textarea v-model="commentText" placeholder="说说这个网站适合什么场景，或有什么使用建议" maxlength="500"></textarea>
          <button type="submit" :disabled="posting">{{ posting ? '发布中' : '发表评论' }}</button>
        </form>
        <p class="message">{{ message }}</p>
        <article v-for="comment in comments" :key="comment.id" class="comment-item">
          <strong>{{ comment.username }}</strong>
          <span>{{ comment.created_at }}</span>
          <p>{{ comment.content }}</p>
        </article>
        <p v-if="comments.length === 0" class="empty">暂无评论</p>
      </section>
    </section>
    <p v-else class="loading">正在加载网站详情...</p>
  </main>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { hasAuthSession, navAPI } from '@/utils/api'

const route = useRoute()
const router = useRouter()
const site = ref(null)
const favoriteIds = ref([])
const comments = ref([])
const commentText = ref('')
const message = ref('')
const posting = ref(false)
const myRating = ref(0)
const showReport = ref(false)
const reportReason = ref('')
const reporting = ref(false)

const favText = computed(() => favoriteIds.value.includes(site.value?.id) ? '取消收藏' : '收藏')
const fallbackLogo = (item) => `https://www.google.com/s2/favicons?sz=128&domain_url=${encodeURIComponent(item.url || '')}`
const requireLogin = (text) => {
  message.value = text
  setTimeout(() => {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
  }, 700)
}

const load = async () => {
  const res = await navAPI.getWebsite(route.params.id)
  site.value = res.data?.data || null
  await loadComments()
  try {
    const fav = await navAPI.getFavorites()
    favoriteIds.value = (fav.data?.data || []).map(item => item.website_id)
  } catch (_) {
    favoriteIds.value = []
  }
}

const loadComments = async () => {
  try {
    const res = await navAPI.getWebsiteComments(route.params.id)
    comments.value = res.data?.data?.items || []
  } catch (_) {
    comments.value = []
  }
}

const visit = async () => {
  if (!site.value) return
  try {
    await navAPI.recordClick(site.value.id)
  } catch (_) {}
  window.open(site.value.url, '_blank', 'noopener,noreferrer')
}

const favorite = async () => {
  if (!site.value) return
  if (!hasAuthSession()) {
    requireLogin('请先登录后收藏')
    return
  }
  try {
    if (favoriteIds.value.includes(site.value.id)) {
      await navAPI.removeFavorite(site.value.id)
      message.value = '已取消收藏'
    } else {
      await navAPI.addFavorite(site.value.id)
      message.value = '已加入收藏'
    }
    await load()
  } catch (error) {
    message.value = error.response?.data?.msg || '收藏操作失败'
  }
}

const rate = async (score) => {
  if (!site.value) return
  if (!hasAuthSession()) {
    requireLogin('请先登录后评分')
    return
  }
  myRating.value = score
  try {
    await navAPI.rateWebsite(site.value.id, score)
    message.value = '评分已保存'
    const res = await navAPI.getWebsite(route.params.id)
    site.value = res.data?.data || site.value
  } catch (error) {
    message.value = error.response?.data?.msg || '评分失败'
  }
}

const postComment = async () => {
  if (!site.value || !commentText.value.trim()) return
  if (!hasAuthSession()) {
    requireLogin('请先登录后发表评论')
    return
  }
  posting.value = true
  try {
    await navAPI.postWebsiteComment(site.value.id, commentText.value.trim())
    commentText.value = ''
    message.value = '评论已发布'
    await loadComments()
  } catch (error) {
    message.value = error.response?.data?.msg || '评论发布失败'
  } finally {
    posting.value = false
  }
}

const submitReport = async () => {
  if (!site.value || !reportReason.value.trim()) return
  if (!hasAuthSession()) {
    requireLogin('请先登录后举报')
    return
  }
  reporting.value = true
  try {
    await navAPI.reportWebsite(site.value.id, reportReason.value.trim())
    reportReason.value = ''
    showReport.value = false
    message.value = '举报已提交，后台会进行处理'
  } catch (error) {
    message.value = error.response?.data?.msg || '举报提交失败'
  } finally {
    reporting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.detail-page { min-height: 100vh; display: grid; place-items: start center; background: #f7f8fb; padding: 32px; color: #172033; }
.detail-panel { width: min(820px, 100%); background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 26px; }
a { color: #2563eb; text-decoration: none; }
.head { display: flex; gap: 18px; align-items: center; margin-top: 18px; }
img { width: 64px; height: 64px; border-radius: 14px; }
h1 { margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }
p, .loading { color: #64748b; }
.meta { display: flex; flex-wrap: wrap; gap: 10px; margin: 22px 0; }
.meta span, .tags span { border: 1px solid #dbe1ec; border-radius: 999px; padding: 6px 10px; color: #475569; font-size: 13px; }
.tags { display: flex; flex-wrap: wrap; gap: 8px; }
footer { display: flex; gap: 12px; margin-top: 24px; }
button { height: 42px; border: 0; border-radius: 6px; padding: 0 18px; background: #111827; color: #fff; font-weight: 700; cursor: pointer; }
button:disabled { opacity: .55; cursor: not-allowed; }
.ghost { background: #eef2f7; color: #111827; }
.rating-box { display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-top: 24px; padding: 16px; border: 1px solid #e6e8ef; border-radius: 8px; background: #fbfcfe; }
.rating-box strong, .rating-box span { display: block; }
.rating-box span { margin-top: 4px; color: #64748b; font-size: 13px; }
.stars { display: flex; gap: 4px; }
.stars button { width: 34px; height: 34px; padding: 0; background: #e5e7eb; color: #94a3b8; }
.stars button.active { background: #111827; color: #facc15; }
.comments { margin-top: 28px; border-top: 1px solid #e6e8ef; padding-top: 22px; }
.report-box { margin-top: 18px; border: 1px solid #e6e8ef; border-radius: 8px; padding: 16px; background: #fbfcfe; }
.report-box h2 { margin: 0 0 12px; font-size: 18px; }
.report-actions { display: flex; gap: 10px; margin-top: 10px; }
.comments h2 { margin: 0 0 14px; font-size: 20px; }
.comments form { display: grid; gap: 10px; }
textarea { min-height: 92px; resize: vertical; border: 1px solid #dbe1ec; border-radius: 8px; padding: 12px; font: inherit; }
.comments form button { justify-self: start; }
.message { min-height: 22px; color: #475569; }
.comment-item { border: 1px solid #eef1f6; border-radius: 8px; padding: 12px; margin-top: 10px; }
.comment-item strong, .comment-item span { display: block; }
.comment-item span { color: #94a3b8; font-size: 12px; margin-top: 2px; }
.comment-item p { margin: 8px 0 0; color: #334155; line-height: 1.6; }
.empty { margin-top: 12px; }
@media (max-width: 640px) {
  .detail-page { padding: 18px; }
  .head, .rating-box, footer { align-items: stretch; flex-direction: column; }
  .report-actions { flex-direction: column; }
  .stars { justify-content: space-between; }
  .stars button { flex: 1; }
}
</style>
