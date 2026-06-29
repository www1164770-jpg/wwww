<template>
  <div class="article-page" v-if="article">
    <h1>{{ article.title }}</h1>
    <div class="meta">发布于 {{ article.created_at }} · {{ article.views }} 浏览</div>
    
    <div class="rich-content" v-html="cleanContent"></div>

    <div class="interaction-bar">
      <button @click="toggleLike" :class="{ active: isLiked }">
        {{ isLiked ? '❤️ 已点赞' : '🤍 点赞' }} ({{ article.likes_count }})
      </button>
    </div>

    <div class="comment-section">
      <h3>评论 ({{ comments.length }})</h3>
      
      <div v-if="isLoggedIn" class="comment-input">
        <textarea v-model="newComment" placeholder="发表友善的评论..."></textarea>
        <button @click="postComment(null)">发表评论</button>
      </div>
      <div v-else class="login-tip">请 <router-link to="/login">登录</router-link> 后发表评论</div>

      <div v-for="comment in commentTree" :key="comment.id" class="comment-item">
        <div class="comment-main">
          <strong>{{ comment.user_name }}</strong>: {{ comment.content }}
          <button v-if="isLoggedIn" @click="replyTo(comment)">回复</button>
          <button v-if="comment.user_id === currentUserId" @click="deleteComment(comment.id)">删除</button>
        </div>
        
        <div class="replies" v-if="comment.children && comment.children.length">
          <div v-for="reply in comment.children" :key="reply.id" class="reply-item">
            <strong>{{ reply.user_name }}</strong> 回复 <strong>{{ reply.reply_to_name }}</strong>: {{ reply.content }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import DOMPurify from 'dompurify' // npm install dompurify
import axios from 'axios'

const route = useRoute()
const article = ref(null)
const comments = ref([])
const isLiked = ref(false)
const newComment = ref('')

// 构建两级评论树的算法
const commentTree = computed(() => {
  const map = {}
  const tree = []
  
  // 1. 初始化一级评论
  comments.value.forEach(c => {
    if (!c.parent_id) {
      map[c.id] = { ...c, children: [] }
      tree.push(map[c.id])
    }
  })
  
  // 2. 挂载二级评论
  comments.value.forEach(c => {
    if (c.parent_id && map[c.parent_id]) {
      map[c.parent_id].children.push(c)
    }
  })
  return tree
})

const cleanContent = computed(() => DOMPurify.sanitize(article.value?.content || ''))

const toggleLike = async () => {
  const res = await axios.post(`/api/articles/${route.params.id}/like`)
  isLiked.value = res.data.data.liked
  article.value.likes_count = res.data.data.count
}

onMounted(async () => {
  // 获取文章详情和评论列表...
})
</script>

<style scoped>
.article-page {
  min-height: 100vh;
  max-width: 860px;
  margin: 0 auto;
  padding: clamp(28px, 6vw, 72px) clamp(18px, 4vw, 32px);
  color: var(--mono-text);
  animation: mono-rise-in 0.64s var(--mono-ease);
}

.article-page h1 {
  margin: 0;
  font-size: clamp(34px, 6vw, 64px);
  font-weight: 860;
  letter-spacing: -0.075em;
  line-height: 1.02;
}

.meta {
  margin-top: 16px;
  color: var(--mono-muted);
  font-size: 14px;
}

.rich-content {
  margin-top: 34px;
  padding: clamp(24px, 4vw, 42px);
  color: var(--mono-text-soft);
  background: var(--mono-surface);
  border: 1px solid var(--mono-border);
  border-radius: var(--mono-radius-xl);
  box-shadow: var(--mono-shadow-sm);
  line-height: 1.9;
}

.rich-content :deep(img) {
  max-width: 100%;
  border-radius: var(--mono-radius-md);
  filter: grayscale(1);
}

.interaction-bar,
.comment-section {
  margin-top: 22px;
  padding: 22px;
  background: var(--mono-surface);
  border: 1px solid var(--mono-border);
  border-radius: var(--mono-radius-lg);
  box-shadow: var(--mono-shadow-sm);
}

.interaction-bar button,
.comment-input button,
.comment-main button {
  padding: 0 18px;
  color: var(--mono-text);
  background: rgba(255,255,255,0.7);
  border: 1px solid var(--mono-border);
  border-radius: 999px;
  transition: transform var(--mono-base) var(--mono-ease), background var(--mono-base) var(--mono-ease);
  filter: grayscale(1);
}

.interaction-bar button:hover,
.comment-input button:hover,
.comment-main button:hover,
.interaction-bar button.active {
  color: #ffffff;
  background: #111111;
  transform: translateY(-2px);
}

.comment-section h3 {
  margin: 0 0 16px;
  font-size: 22px;
  letter-spacing: -0.04em;
}

.comment-input {
  display: grid;
  gap: 12px;
  margin-bottom: 18px;
}

.comment-input textarea {
  min-height: 112px;
  padding: 14px 16px;
  resize: vertical;
}

.login-tip {
  margin-bottom: 16px;
  color: var(--mono-muted);
}

.comment-item {
  padding: 16px 0;
  border-top: 1px solid var(--mono-border);
  animation: mono-rise-in 0.5s var(--mono-ease);
}

.comment-main {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  line-height: 1.7;
}

.replies {
  margin: 12px 0 0 18px;
  padding-left: 14px;
  border-left: 1px solid var(--mono-border);
}

.reply-item {
  padding: 8px 0;
  color: var(--mono-text-soft);
}
</style>
