<template>
  <img
    v-if="!imgError"
    :src="faviconUrl"
    @error="handleError"
    :alt="name"
    class="site-icon"
  />
  <span v-else class="fallback-text">{{ fallbackLetter }}</span>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  url: { type: String, required: true },
  name: { type: String, default: '' }
})

const imgError = ref(false)

// 首字母备用显示（当图标加载失败时）
const fallbackLetter = computed(() => {
  if (props.name) return props.name.charAt(0).toUpperCase()
  try {
    const hostname = new URL(props.url).hostname
    return hostname.replace('www.', '').charAt(0).toUpperCase()
  } catch {
    return '?'
  }
})

// 使用 Google 的 favicon 服务，稳定、支持 HTTPS，国内可用
const faviconUrl = computed(() => {
  try {
    const domain = new URL(props.url).hostname
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`
  } catch {
    // 如果 URL 格式不合法，返回空字符串，触发 fallback
    return ''
  }
})

const handleError = () => {
  imgError.value = true
}
</script>

<style scoped>
.site-icon {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: inherit;
}

.fallback-text {
  font-weight: 600;
  color: white;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.2);
  border-radius: inherit;
}
</style>