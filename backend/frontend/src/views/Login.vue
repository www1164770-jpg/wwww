<template>
  <div class="login-page">
    <div class="guard-container block-shadow">
      <div id="authing-container"></div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { Guard } from '@authing/guard';
import '@authing/guard/dist/esm/guard.min.css';

onMounted(() => {
  // 1. 初始化核心引擎 (⚠️ 这里的 appId 必须填对，否则会直接变 null 导致白屏！)
  // 1. 初始化核心引擎 
  const authing = new Guard({
    appId: '69fdee93f62848c14ce9d3a6', 
    mode: 'normal',
    
    // ✨ 核心修改点：默认展示邮箱和密码的输入框
    defaultLoginMethod: 'email-password', 
    
    // ✨ 告诉 Guard 你想要在界面上画出哪些登录选项卡
    // 'email-password' = 邮箱密码登录
    // 'email-code' = 邮箱验证码登录
    // 'phone-code' = 手机验证码
    loginMethods: ['email-password', 'email-code', 'phone-code'],
    
    // 第三方登录保持不变
    socialConnections: ['github', 'wechat:pc', 'google'],
    isSSO: false,
  });

  // 2. 强行挂载到页面上
  authing.start('#authing-container');

  // 3. 监听登录成功并强制跳转
// 3. 监听登录成功并强制跳转
  authing.on('login', (userInfo) => {
    console.log('登录成功，完整数据:', userInfo);
    // 提取 Token
    const token = userInfo.token || 
                  userInfo.idToken || 
                  userInfo.accessToken || 
                  (userInfo.data && userInfo.data.token) ||
                  (userInfo.data && userInfo.data.id_token);

    if (token) {
      localStorage.setItem('access_token', token);
      localStorage.setItem('is_logged_in', 'true');
      
      // ✨ 完美提取用户名，如果没有就叫“智汇导航用户”
      const username = userInfo.username || userInfo.nickname || (userInfo.data && userInfo.data.username) || '智汇导航用户';
      
      // ✨ 完美提取头像！(如果第三方没提供头像，给一个超级好看的默认渐变头像)
      const avatar = userInfo.photo || userInfo.avatar || (userInfo.data && userInfo.data.photo) || 'https://api.dicebear.com/7.x/identicon/svg?seed=' + username;

      // 存入包含完整信息的对象
      localStorage.setItem('user_info', JSON.stringify({ username, avatar }));

      // 物理级跳转首页
      window.location.href = '/';
    } else {
      alert('未提取到 Token！');
    }
  });
});
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f8fafc; 
}
.guard-container {
  padding: 20px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  min-width: 360px; 
  min-height: 400px;
}
</style>