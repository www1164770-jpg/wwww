<template>
  <main class="mvp-page">
    <section class="mvp-panel">
      <p class="eyebrow">个性化推荐</p>
      <h1>选择你的需求</h1>
      <p class="desc">系统会根据你的职业方向和当前目标推荐更合适的网站。</p>
      <div class="option-grid">
        <button
          v-for="item in options"
          :key="item.key"
          type="button"
          :class="{ active: selected.includes(item.key) }"
          @click="toggle(item.key)"
        >
          <strong>{{ item.label }}</strong>
          <span>{{ item.desc }}</span>
        </button>
      </div>
      <footer>
        <p>{{ message }}</p>
        <button class="primary" :disabled="loading || selected.length === 0" @click="submit">
          {{ loading ? '保存中' : '生成推荐' }}
        </button>
      </footer>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { userAPI } from '@/utils/api'

const router = useRouter()
const selected = ref(['self-learning'])
const loading = ref(false)
const message = ref('')
const options = [
  { key: 'frontend', label: '前端开发', desc: '框架、文档、组件与工程化' },
  { key: 'backend', label: '后端开发', desc: '接口、数据库、部署与开源' },
  { key: 'ai-data', label: 'AI 工具', desc: '对话、绘图、编程和效率' },
  { key: 'ui-design', label: '设计创作', desc: '灵感、素材、原型和图像' },
  { key: 'self-learning', label: '学习提升', desc: '课程、文档、知识库' },
  { key: 'job-hunting', label: '求职面试', desc: '刷题、简历、面试准备' },
  { key: 'efficiency', label: '办公效率', desc: '文档、协作、转换工具' },
  { key: 'open-source', label: '开源资源', desc: '代码托管与项目发现' }
]

const toggle = (key) => {
  selected.value = selected.value.includes(key)
    ? selected.value.filter(item => item !== key)
    : [...selected.value, key]
}

const submit = async () => {
  loading.value = true
  try {
    const res = await userAPI.submitSurvey(selected.value)
    message.value = res.data?.msg || '已保存'
    router.push('/')
  } catch (error) {
    message.value = error.response?.data?.msg || '保存失败，请先登录'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.mvp-page { min-height: 100vh; background: #f6f7fb; padding: 32px; color: #172033; }
.mvp-panel { max-width: 920px; margin: 0 auto; background: #fff; border: 1px solid #e6e8ef; border-radius: 8px; padding: 28px; }
.eyebrow { margin: 0 0 8px; color: #64748b; font-size: 13px; }
h1 { margin: 0; font-size: 30px; }
.desc { color: #64748b; margin-bottom: 22px; }
.option-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
.option-grid button { text-align: left; border: 1px solid #dbe1ec; background: #fff; border-radius: 8px; padding: 16px; cursor: pointer; }
.option-grid button.active { border-color: #111827; background: #f1f5f9; }
strong, span { display: block; }
span { margin-top: 6px; color: #64748b; font-size: 13px; }
footer { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 22px; }
.primary { border: 0; background: #111827; color: #fff; border-radius: 6px; height: 42px; padding: 0 18px; font-weight: 700; cursor: pointer; }
.primary:disabled { opacity: .55; cursor: not-allowed; }
@media (max-width: 640px) { footer { align-items: stretch; flex-direction: column; } }
</style>
