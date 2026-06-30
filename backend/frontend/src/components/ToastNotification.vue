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
  gap: 10px;
  padding: 12px 24px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  color: var(--mono-text);
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid var(--mono-border);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  box-shadow: var(--mono-shadow-md);
  max-width: 90vw;
  word-break: break-word;
}
.toast-icon {
  filter: grayscale(1);
}
.toast-success {
  border-color: rgba(17, 17, 17, 0.22);
}
.toast-error {
  border-color: rgba(17, 17, 17, 0.34);
  box-shadow: 0 10px 34px rgba(17, 17, 17, 0.18);
}
.toast-info {
  border-color: var(--mono-border);
}
.toast-warning {
  border-color: rgba(17, 17, 17, 0.28);
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
