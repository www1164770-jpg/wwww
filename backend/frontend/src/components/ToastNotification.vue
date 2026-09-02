<template>
  <!-- 🍞 全局轻提示 -->
  <Teleport to="body">
    <transition name="toast-slide">
      <div
        v-if="visible"
        class="toast-container"
        :class="'toast-' + type"
        @click="dismiss"
      >
        <span class="toast-icon">{{ iconMap[type] || "💬" }}</span>
        <span class="toast-text">{{ message }}</span>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  message: { type: String, default: "" },
  type: { type: String, default: "info" }, // 'success' | 'error' | 'info' | 'warning'
  duration: { type: Number, default: 3000 },
});

const emit = defineEmits(["dismiss"]);

const visible = ref(false);
let timer = null;

const iconMap = {
  success: "✅",
  error: "❌",
  info: "💬",
  warning: "⚠️",
};

watch(
  () => props.message,
  (newMsg) => {
    if (!newMsg) return;
    visible.value = true;
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      visible.value = false;
      emit("dismiss");
    }, props.duration);
  },
);

function dismiss() {
  visible.value = false;
  if (timer) clearTimeout(timer);
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
  gap: 8px;
  padding: 10px 16px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  color: var(--app-text-primary);
  background: var(--app-button-bg);
  border: 1px solid var(--app-button-border);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  box-shadow: var(--app-button-shadow);
  max-width: 90vw;
  word-break: break-word;
}
.toast-icon {
  filter: grayscale(1);
  opacity: 0.78;
}
.toast-success {
  border-color: rgba(34, 197, 94, 0.28);
}
.toast-success .toast-icon {
  filter: none;
}
.toast-error {
  border-color: rgba(239, 68, 68, 0.3);
}
.toast-info {
  border-color: var(--app-button-border);
}
.toast-warning {
  border-color: rgba(245, 158, 11, 0.3);
}

.toast-slide-enter-active {
  transition: all 0.3s var(--mono-ease);
}
.toast-slide-leave-active {
  transition: all 0.2s ease-in;
}
.toast-slide-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}
.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}
</style>
