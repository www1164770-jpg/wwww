<template>
  <main class="mvp-page">
    <section class="mvp-panel">
      <p class="eyebrow">智汇导航</p>
      <h1>创建账号</h1>
      <form class="mvp-form" @submit.prevent="submit">
        <input v-model.trim="form.username" placeholder="用户名" required />
        <input v-model.trim="form.email" placeholder="邮箱" type="email" required />
        <input v-model.trim="form.code" placeholder="邮箱验证码" required />
        <input v-model="form.password" placeholder="密码" type="password" required />
        <button type="button" @click="sendCode" :disabled="sending || countdown > 0">
          {{ codeButtonText }}
        </button>
        <button type="submit" :disabled="loading">{{ loading ? '注册中' : '注册并登录' }}</button>
      </form>
      <p class="mvp-message" :class="{ error: isError }">{{ message }}</p>
      <RouterLink to="/login">已有账号，去登录</RouterLink>
    </section>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { authAPI, setAuthSession } from '@/utils/api'

const router = useRouter()
const form = reactive({ username: '', email: '', code: '', password: '' })
const loading = ref(false)
const sending = ref(false)
const message = ref('')
const isError = ref(false)
const countdown = ref(0)
let timer = null

const codeButtonText = computed(() => {
  if (sending.value) return '发送中'
  if (countdown.value > 0) return `${countdown.value} 秒后重发`
  return '发送验证码'
})

const startCountdown = () => {
  countdown.value = 60
  if (timer) clearInterval(timer)
  timer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      clearInterval(timer)
      timer = null
    }
  }, 1000)
}

const sendCode = async () => {
  if (!form.email) {
    message.value = '请先填写邮箱'
    isError.value = true
    return
  }
  sending.value = true
  message.value = ''
  isError.value = false
  try {
    const res = await authAPI.sendCode(form.email)
    message.value = res.data?.msg || '验证码已发送'
    isError.value = false
    startCountdown()
  } catch (error) {
    message.value = error.response?.data?.msg || '验证码发送失败'
    isError.value = true
  } finally {
    sending.value = false
  }
}

const submit = async () => {
  loading.value = true
  message.value = ''
  isError.value = false
  try {
    const res = await authAPI.register(form)
    if (res.data?.code === 0) {
      const login = await authAPI.login(form.email, form.password)
      const data = login.data?.data || {}
      const token = data.access_token || data.token || login.data?.access_token || login.data?.token
      const refreshToken = data.refresh_token || login.data?.refresh_token || ''
      const user = data.user || {}
      if (token) {
        setAuthSession({
          accessToken: token,
          refreshToken,
          user: {
            username: user.username || form.username,
            email: user.email || form.email,
            avatar: user.avatar || `https://api.dicebear.com/7.x/identicon/svg?seed=${encodeURIComponent(form.username)}`,
            has_survey: 0,
            user_tags: ''
          }
        })
      }
      router.push('/questionnaire')
      return
    }
    message.value = res.data?.msg || '注册失败'
    isError.value = true
  } catch (error) {
    message.value = error.response?.data?.msg || '注册失败'
    isError.value = true
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.mvp-page { min-height: 100vh; display: grid; place-items: center; background: #f6f7fb; color: #172033; }
.mvp-panel { width: min(420px, calc(100% - 32px)); background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 28px; box-shadow: 0 18px 45px rgba(20, 28, 45, .08); }
.eyebrow { margin: 0 0 8px; color: #64748b; font-size: 13px; }
h1 { margin: 0 0 20px; font-size: 28px; letter-spacing: 0; }
.mvp-form { display: grid; gap: 12px; }
input { height: 44px; border: 1px solid #d9deea; border-radius: 6px; padding: 0 12px; font-size: 14px; }
button { height: 44px; border: 0; border-radius: 6px; background: #111827; color: #fff; font-weight: 700; cursor: pointer; }
button[type="button"] { background: #eef2f7; color: #111827; }
button:disabled { opacity: .55; cursor: not-allowed; }
.mvp-message { min-height: 20px; color: #475569; line-height: 1.5; }
.mvp-message.error { color: #b91c1c; }
a { color: #2563eb; text-decoration: none; }
</style>
