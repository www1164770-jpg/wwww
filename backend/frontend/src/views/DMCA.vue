<template>
  <main class="dmca-page">
    <section class="dmca-panel">
      <RouterLink to="/" class="back-link">返回首页</RouterLink>
      <header>
        <p>版权与合规</p>
        <h1>DMCA 版权投诉</h1>
        <span>如果你认为本站收录的网站或内容侵犯了你的版权，请提交以下信息，我们会尽快核实处理。</span>
      </header>

      <form class="dmca-form" @submit.prevent="submitDMCA">
        <label>
          投诉方名称 / 版权方
          <input v-model.trim="form.name" type="text" required />
        </label>
        <label>
          联系邮箱
          <input v-model.trim="form.email" type="email" required />
        </label>
        <label>
          侵权内容链接
          <input v-model.trim="form.url" type="url" required />
        </label>
        <label>
          侵权描述与权属证明
          <textarea v-model.trim="form.desc" required rows="6"></textarea>
        </label>
        <button type="submit" :disabled="isSubmitting">{{ isSubmitting ? '提交中...' : '提交版权投诉' }}</button>
      </form>

      <p class="message" :class="{ success: success }">{{ message }}</p>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import api from '@/utils/api'

const form = reactive({ name: '', email: '', url: '', desc: '' })
const isSubmitting = ref(false)
const message = ref('')
const success = ref(false)

const submitDMCA = async () => {
  isSubmitting.value = true
  message.value = ''
  success.value = false
  try {
    const res = await api.post('/dmca', form)
    message.value = res.data?.msg || '版权投诉已提交'
    success.value = true
    Object.assign(form, { name: '', email: '', url: '', desc: '' })
  } catch (error) {
    message.value = error.response?.data?.msg || '提交失败，请稍后重试'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.dmca-page { min-height: 100vh; display: grid; place-items: start center; background: #f6f7fb; color: #172033; padding: 32px; }
.dmca-panel { width: min(760px, 100%); background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 28px; }
.back-link { color: #2563eb; text-decoration: none; font-size: 14px; }
header { margin: 22px 0; }
header p { margin: 0 0 6px; color: #64748b; font-size: 13px; }
h1 { margin: 0 0 10px; font-size: 30px; letter-spacing: 0; }
header span { color: #64748b; line-height: 1.7; }
.dmca-form { display: grid; gap: 14px; }
label { display: grid; gap: 8px; color: #334155; font-weight: 700; }
input, textarea { border: 1px solid #dbe1ec; border-radius: 6px; padding: 0 12px; font: inherit; color: #172033; }
input { height: 42px; }
textarea { min-height: 132px; padding-top: 12px; resize: vertical; }
button { height: 42px; border: 0; border-radius: 6px; background: #111827; color: #fff; font-weight: 700; cursor: pointer; }
button:disabled { opacity: .55; cursor: not-allowed; }
.message { min-height: 22px; color: #b91c1c; }
.message.success { color: #166534; }
@media (max-width: 640px) {
  .dmca-page { padding: 18px; }
  .dmca-panel { padding: 20px; }
}
</style>
