<template>
  <div v-if="visible" class="modal-backdrop" @click.self="$emit('close')">
    <section class="modal">
      <button class="close" type="button" @click="$emit('close')">×</button>
      <h2>外观设置</h2>
      <label class="toggle">
        <span>深色模式</span>
        <input :checked="darkMode" type="checkbox" @change="$emit('update:darkMode', $event.target.checked)">
      </label>
    </section>
  </div>
</template>

<script setup>
defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  darkMode: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:darkMode', 'close'])
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, .45);
}

.modal {
  position: relative;
  width: min(380px, 100%);
  border-radius: 8px;
  padding: 28px;
  background: #fff;
}

h2 {
  margin: 0 0 18px;
}

.toggle {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
}

.close {
  position: absolute;
  top: 12px;
  right: 12px;
  border: 0;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
}
</style>
