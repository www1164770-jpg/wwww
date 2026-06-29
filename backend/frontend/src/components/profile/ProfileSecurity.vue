<template>
  <section class="panel">
    <div class="heading">
      <p>安全设置</p>
      <h1>账号与设备</h1>
    </div>
    <div class="list-card">
      <div class="row">
        <span>登录状态</span>
        <strong>已通过本地令牌登录</strong>
      </div>
      <div class="row">
        <span>绑定邮箱</span>
        <strong>{{ userInfo.email || '未绑定' }}</strong>
      </div>
      <div v-for="device in devices" :key="device.id || device.name" class="row">
        <span>{{ device.name || '登录设备' }}</span>
        <strong>{{ device.location || '未知位置' }} {{ device.time || '' }}</strong>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  userInfo: {
    type: Object,
    required: true
  },
  devices: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.panel {
  display: grid;
  gap: 20px;
}

.heading p,
.heading h1 {
  margin: 0;
}

.heading p {
  color: #1769aa;
  font-weight: 700;
}

.list-card {
  display: grid;
  max-width: 760px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-bottom: 1px solid #eef3f8;
}

.row:last-child {
  border-bottom: 0;
}

span {
  color: #64748b;
}
</style>
