<template>
  <div class="login-container">
    <div class="login-card">
      <!-- Logo 区域 -->
      <div class="brand">
        <span class="logo-emoji">🚀</span>
        <h2>智汇导航</h2>
        <p class="subtitle">{{ isLogin ? '欢迎回来，请登录' : '创建你的专属账号' }}</p>
      </div>

      <!-- 表单区域 -->
      <form @submit.prevent="handleSubmit" class="form-body">
        <!-- 注册时才需要用户名 -->
        <div class="input-group" v-if="!isLogin">
          <label>用户名</label>
          <input type="text" v-model="form.username" placeholder="请输入昵称" required />
        </div>

        <div class="input-group">
          <label>邮箱</label>
          <input type="email" v-model="form.email" placeholder="请输入你的邮箱" required />
        </div>

        <div class="input-group">
          <label>密码</label>
          <input type="password" v-model="form.password" placeholder="请输入密码" required />
        </div>

        <button type="submit" class="submit-btn" :disabled="loading">
          {{ loading ? '处理中...' : (isLogin ? '登 录' : '注 册') }}
        </button>
      </form>

      <!-- 切换状态 -->
      <div class="toggle-text">
        <span>{{ isLogin ? '还没有账号？' : '已有账号？' }}</span>
        <a href="#" @click.prevent="isLogin = !isLogin">
          {{ isLogin ? '立即注册' : '直接登录' }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
// 引入我们上一轮写好的 api 函数 (请确保路径匹配你的实际情况)
import { loginUser, registerUser } from '../utils/api'; 

const router = useRouter();

// 状态控制
const isLogin = ref(true); // true 为登录模式，false 为注册模式
const loading = ref(false);

// 表单数据
const form = reactive({
  username: '',
  email: '',
  password: ''
});

// 处理提交
const handleSubmit = async () => {
  loading.value = true;
  try {
    if (isLogin.value) {
      // 💥 执行登录
      const res = await loginUser({ email: form.email, password: form.password });
      // 保存金钥匙到本地
      localStorage.setItem('access_token', res.data.access_token);
      localStorage.setItem('refresh_token', res.data.refresh_token);
      localStorage.setItem('is_logged_in', 'true'); 
      
      // 存入一个基础的用户信息给 Home.vue 用来显示头像和名字
      // (如果你的后端 login 接口有返回真实的 user 数据，可以用 res.data.user 替换)
      localStorage.setItem('user_info', JSON.stringify({
        username: form.email.split('@')[0], // 暂时用邮箱前缀当默认昵称
        email: form.email,
        avatar: '' 
      }));
      alert('登录成功！欢迎回来。');
      
      // 跳转回首页
      window.location.href = '/';
    } else {
      // 💥 执行注册
      await registerUser(form);
      alert('注册成功！请直接登录。');
      isLogin.value = true; // 注册成功后，自动切回登录面板
      form.password = '';   // 清空密码让用户重新输入
    }
  } catch (error) {
    // 提取后端报错信息
    const errorMsg = error.response?.data?.error || '网络请求失败，请稍后再试';
    alert(`出错了：${errorMsg}`);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* 居中大背景 */
.login-container {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f3f4f6; /* 如果你有暗黑模式，这里可以改成 var(--bg-color) */
}

/* 拟物/Bento风格卡片 */
.login-card {
  background: white;
  padding: 40px;
  border-radius: 24px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.08);
  width: 100%;
  max-width: 400px;
  transition: all 0.3s ease;
}

.brand {
  text-align: center;
  margin-bottom: 30px;
}
.logo-emoji {
  font-size: 48px;
}
.brand h2 {
  margin: 10px 0 5px;
  font-size: 24px;
  color: #1a1a1a;
}
.subtitle {
  color: #666;
  font-size: 14px;
}

.input-group {
  margin-bottom: 20px;
}
.input-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}
.input-group input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  font-size: 15px;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.input-group input:focus {
  outline: none;
  border-color: #3b82f6; /* 你的主题蓝 */
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: transform 0.1s, background 0.2s;
}
.submit-btn:hover {
  background: #2563eb;
}
.submit-btn:active {
  transform: scale(0.98);
}
.submit-btn:disabled {
  background: #93c5fd;
  cursor: not-allowed;
}

.toggle-text {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: #666;
}
.toggle-text a {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 600;
  margin-left: 5px;
}
.toggle-text a:hover {
  text-decoration: underline;
}
</style>