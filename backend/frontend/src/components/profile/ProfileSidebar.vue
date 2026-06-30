<template>
  <aside class="profile-sidebar">
    <button class="back-home" type="button" @click="$emit('back-home')">
      返回首页
    </button>

    <div class="profile-brief">
      <img
        :src="userInfo.avatar || fallbackAvatar"
        alt="用户头像"
        @error="$event.target.src = fallbackAvatar"
      />
      <strong>{{ userInfo.username || "未命名用户" }}</strong>
      <span>{{ userInfo.email || "已登录账号" }}</span>
    </div>

    <nav aria-label="个人中心导航">
      <button
        v-for="item in tabs"
        :key="item.key"
        type="button"
        :class="{ active: activeTab === item.key }"
        @click="$emit('update:activeTab', item.key)"
      >
        {{ item.label }}
      </button>
    </nav>

    <button class="logout" type="button" @click="$emit('logout')">
      退出当前账号
    </button>
  </aside>
</template>

<script setup>
defineProps({
  activeTab: {
    type: String,
    required: true,
  },
  userInfo: {
    type: Object,
    required: true,
  },
});

defineEmits(["update:activeTab", "back-home", "logout"]);

const fallbackAvatar =
  "https://api.dicebear.com/7.x/avataaars/svg?seed=fallback";
const tabs = [
  { key: "homepage", label: "个人主页" },
  { key: "basic", label: "基础资料" },
  { key: "security", label: "安全设置" },
  { key: "privacy", label: "隐私偏好" },
  { key: "content", label: "内容管理" },
  { key: "history", label: "互动足迹" },
];
</script>

<style scoped>
.profile-sidebar {
  display: grid;
  align-content: start;
  gap: 22px;
  min-height: 100vh;
  border-right: 1px solid #dbe4ef;
  padding: 24px;
  background: #fff;
}

.back-home,
nav button,
.logout {
  border: 0;
  border-radius: 6px;
  padding: 11px 12px;
  text-align: left;
  background: #edf3fa;
  cursor: pointer;
}

.profile-brief {
  display: grid;
  gap: 8px;
  justify-items: center;
  border-radius: 8px;
  padding: 20px;
  background: #f7fafc;
}

img {
  width: 72px;
  height: 72px;
  border-radius: 50%;
}

span {
  color: #64748b;
  font-size: 13px;
}

nav {
  display: grid;
  gap: 8px;
}

nav button.active,
nav button:hover {
  color: #fff;
  background: #1769aa;
}

.logout {
  color: #b91c1c;
  background: #fee2e2;
}
</style>
