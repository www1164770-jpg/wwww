<template>
  <!-- 🍞 全局轻提示 -->
  <Teleport to="body">
    <transition name="toast-slide">
      <div v-if="visible" class="toast-container" :class="'toast-' + type" @click="dismiss">
        <span class="toast-icon">{{ iconMap[type] || '💬' }}</span>
        <span class="toast-text">{{ message }}</span>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  message: { type: String, default: '' },
  type: { type: String, default: 'info' }, // 'success' | 'error' | 'info' | 'warning'
  duration: { type: Number, default: 3000 }
})

const emit = defineEmits(['dismiss'])

const visible = ref(false)
let timer = null

const iconMap = {
  success: '✅',
  error: '❌',
  info: '💬',
  warning: '⚠️'
}

watch(() => props.message, (newMsg) => {
  if (!newMsg) return
  visible.value = true
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    visible.value = false
    emit('dismiss')
  }, props.duration)
})

function dismiss() {
  visible.value = false
  if (timer) clearTimeout(timer)
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10000;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 28px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
  max-width: 90vw;
  word-break: break-word;
}
.toast-success { background: rgba(16, 185, 129, 0.92); color: #fff; }
.toast-error   { background: rgba(239, 68, 68, 0.92); color: #fff; }
.toast-info    { background: rgba(59, 130, 246, 0.92); color: #fff; }
.toast-warning { background: rgba(245, 158, 11, 0.92); color: #fff; }

.toast-slide-enter-active { transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); }
.toast-slide-leave-active { transition: all 0.2s ease-in; }
.toast-slide-enter-from  { opacity: 0; transform: translateX(-50%) translateY(-20px); }
.toast-slide-leave-to    { opacity: 0; transform: translateX(-50%) translateY(-10px); }
</style>
