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