<template>
  <div class="profile-page">
    <div class="profile-card">
      <h1>账号管理</h1>
      <div class="user-info-section">
        <img :src="userInfo.avatar" class="large-avatar">
        <h2>{{ userInfo.username }}</h2>
        <p class="user-email">已连接 GitHub 账号</p>
      </div>

      <div class="action-list">
        <div class="action-item" @click="handleEditName">
          <span>修改昵称</span>
          <span class="arrow"> > </span>
        </div>
        <div class="action-item logout" @click="doLogout">
          <span>安全退出</span>
        </div>
      </div>
      
      <button class="back-home" @click="$router.push('/')">返回首页</button>
    </div>
  </div>
</template>

<script setup>
// 这里编写修改名字和退出的逻辑（从 App.vue 搬过来即可）
</script>

<style scoped>
/* 这里写你的个人中心样式，建议使用大背景+中央白色/深色卡片的布局 */
.profile-page {
  display: flex;
  justify-content: center;
  padding-top: 100px;
  background: var(--bg-main);
  min-height: 100vh;
}
.profile-card {
  width: 100%;
  max-width: 500px;
  text-align: center;
}
</style>