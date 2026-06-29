<template>
  <div v-if="visible" class="modal-backdrop" @click.self="$emit('close')">
    <section class="modal">
      <button class="close" type="button" @click="$emit('close')">×</button>
      <h2>登录智慧导航</h2>
      <p>登录后可以同步收藏、提交网站并进入个人中心。</p>
      <RouterLink class="primary" to="/login" @click="$emit('close')">前往登录</RouterLink>
    </section>
  </div>
</template>

<script setup>
defineProps({
  visible: {
    type: Boolean,
    default: false
  }
})

defineEmits(['close'])
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
  width: min(420px, 100%);
  border-radius: 8px;
  padding: 28px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(15, 23, 42, .24);
}

h2,
p {
  margin: 0;
}

p {
  margin-top: 10px;
  color: #64748b;
  line-height: 1.6;
}

.primary {
  display: inline-flex;
  margin-top: 22px;
  border-radius: 6px;
  padding: 11px 16px;
  color: #fff;
  background: #18212f;
  text-decoration: none;
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
