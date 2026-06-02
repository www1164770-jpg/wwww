<template>
  <div id="app-root">
    <router-view></router-view> 
  </div>
  <transition name="slide-up">
    <div v-if="showConsent" class="cookie-banner block-shadow">
      <div class="cookie-content">
        <span class="cookie-icon">🍪</span>
        <p>我们使用 Cookie 来提升您的浏览体验、分析网站流量并提供个性化内容。继续使用即表示您同意我们的<router-link to="/privacy">隐私政策</router-link>。</p>
      </div>
      <div class="cookie-actions">
        <button class="btn-cancel" @click="handleConsent('rejected')">仅必要</button>
        <button class="btn-primary" @click="handleConsent('accepted')">接受全部</button>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const showConsent = ref(false)

onMounted(() => {
  if (!localStorage.getItem('cookie_consent_status')) {
    showConsent.value = true
  }
})

const handleConsent = (status) => {
  localStorage.setItem('cookie_consent_status', status)
  showConsent.value = false
}
</script>

<style scoped>
.cookie-banner {
  position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
  width: 90%; max-width: 600px; z-index: 99999;
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 24px; background: rgba(255,255,255,0.9);
  backdrop-filter: blur(20px); border-radius: 16px;
}
.cookie-content { display: flex; gap: 12px; align-items: center; font-size: 13px; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translate(-50%, 50px); }
.slide-up-enter-active, .slide-up-leave-active { transition: all 0.5s ease; }
</style>

<style>
body { margin: 0; padding: 0; font-family: sans-serif; }
/* 强制显示垂直滚动条，彻底杜绝因滚动条时隐时现导致的页面左右晃动 */
html {
  overflow-y: scroll; 
}
</style>