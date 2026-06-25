<template>
  <main class="login-page">
    <section class="login-panel">
      <p class="eyebrow">智汇导航</p>
      <h1>登录账号</h1>
      <p class="desc">登录后可以同步收藏、完成问卷，并获得更贴合需求的网站推荐。</p>

      <form class="login-form" @submit.prevent="submit">
        <input v-model.trim="account" placeholder="用户名或邮箱" autocomplete="username" required />
        <input v-model="password" placeholder="密码" type="password" autocomplete="current-password" required />
        <button type="submit" :disabled="loading">{{ loading ? '登录中' : '登录' }}</button>
      </form>

      <p class="message">{{ message }}</p>
      <footer>
        <RouterLink to="/register">注册账号</RouterLink>
        <RouterLink to="/">返回首页</RouterLink>
      </footer>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authAPI, setAuthSession } from '../utils/api'

const route = useRoute()
const router = useRouter()
const account = ref('')
const password = ref('')
const loading = ref(false)
const message = ref('')

const submit = async () => {
  loading.value = true
  message.value = ''
  try {
    const res = await authAPI.login(account.value, password.value)
    if (res.data?.code !== 0) {
      message.value = res.data?.msg || '登录失败'
      return
    }

    const data = res.data?.data || {}
    const token = data.access_token || data.token || res.data.access_token || res.data.token
    const refreshToken = data.refresh_token || res.data.refresh_token || ''
    const user = data.user || { username: account.value }

    if (!token) {
      message.value = '登录失败，后端未返回访问令牌'
      return
    }

    setAuthSession({
      accessToken: token,
      refreshToken,
      user: {
        username: user.username || account.value,
        email: user.email || '',
        avatar: user.avatar || `https://api.dicebear.com/7.x/identicon/svg?seed=${encodeURIComponent(user.username || account.value)}`,
        has_survey: user.has_survey || 0,
        user_tags: user.user_tags || ''
      }
    })

    router.push(route.query.redirect || '/')
  } catch (error) {
    message.value = error.response?.data?.msg || '登录失败，请检查账号或密码'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; display: grid; place-items: center; background: #f6f7fb; color: #172033; padding: 24px; }
.login-panel { width: min(420px, 100%); background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 28px; box-shadow: 0 18px 45px rgba(20, 28, 45, .08); }
.eyebrow { margin: 0 0 8px; color: #64748b; font-size: 13px; }
h1 { margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }
.desc { margin: 0 0 20px; color: #64748b; line-height: 1.6; }
.login-form { display: grid; gap: 12px; }
input { height: 44px; border: 1px solid #d9deea; border-radius: 6px; padding: 0 12px; font-size: 14px; }
button { height: 44px; border: 0; border-radius: 6px; background: #111827; color: #fff; font-weight: 700; cursor: pointer; }
button:disabled { opacity: .55; cursor: not-allowed; }
.message { min-height: 22px; color: #b91c1c; }
footer { display: flex; justify-content: space-between; gap: 12px; }
a { color: #2563eb; text-decoration: none; }
@media (max-width: 520px) {
  footer { flex-direction: column; }
}
</style>
