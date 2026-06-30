/**
 * 用户全局状态管理 (Pinia Store)
 * =====================================
 * 管理用户登录态、个人信息、Token 等核心状态。
 * 替代原先散落在 Home.vue 和其他组件中的 localStorage 直接读写。
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { userAPI, authAPI } from "@/utils/api";

export const useUserStore = defineStore("user", () => {
  // ==================== 状态 ====================
  const isLoggedIn = ref(false);
  const accessToken = ref(null);
  const refreshToken = ref(null);
  const userInfo = ref({
    username: "",
    avatar: "",
    email: "未绑定邮箱",
    phone: "",
    gender: "保密",
    birthday: "未设置",
    bio: "这个人很懒，什么都没写~",
  });

  // ==================== 计算属性 ====================
  const username = computed(() => userInfo.value.username);
  const avatar = computed(
    () =>
      userInfo.value.avatar ||
      "https://api.dicebear.com/7.x/avataaars/svg?seed=fallback",
  );

  // ==================== 初始化（从 localStorage 恢复） ====================
  function initFromStorage() {
    const savedToken = localStorage.getItem("access_token");
    const savedRefresh = localStorage.getItem("refresh_token");
    const savedLogin = localStorage.getItem("is_logged_in");
    const savedUser = localStorage.getItem("user_info");

    if (savedToken && savedLogin === "true") {
      accessToken.value = savedToken;
      refreshToken.value = savedRefresh;
      isLoggedIn.value = true;
      if (savedUser) {
        try {
          userInfo.value = { ...userInfo.value, ...JSON.parse(savedUser) };
        } catch (e) {
          console.warn("解析本地用户信息失败");
        }
      }
    }
  }

  // ==================== 持久化到 localStorage ====================
  function persistToStorage() {
    if (accessToken.value)
      localStorage.setItem("access_token", accessToken.value);
    if (refreshToken.value)
      localStorage.setItem("refresh_token", refreshToken.value);
    localStorage.setItem("is_logged_in", isLoggedIn.value ? "true" : "false");
    localStorage.setItem("user_info", JSON.stringify(userInfo.value));
  }

  // ==================== 登录（处理 OAuth 回调参数） ====================
  function loginFromUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("access_token");
    const refresh = params.get("refresh_token");

    if (token) {
      accessToken.value = token;
      refreshToken.value = refresh || null;
      isLoggedIn.value = true;

      // 从 URL 参数提取用户信息
      const username = params.get("username") || "";
      const email = params.get("email") || "";
      const avatar = params.get("avatar") || "";

      if (username) {
        userInfo.value = {
          ...userInfo.value,
          username,
          email: email || userInfo.value.email,
          avatar: avatar || userInfo.value.avatar,
        };
      }

      persistToStorage();
      // 清理 URL 参数
      window.history.replaceState({}, document.title, "/");
      return true;
    }
    return false;
  }

  // ==================== 手动设置用户信息 ====================
  function setUserInfo(info) {
    userInfo.value = { ...userInfo.value, ...info };
    persistToStorage();
  }

  // ==================== 退出登录 ====================
  function logout() {
    accessToken.value = null;
    refreshToken.value = null;
    isLoggedIn.value = false;
    userInfo.value = {
      username: "",
      avatar: "",
      email: "未绑定邮箱",
      phone: "",
      gender: "保密",
      birthday: "未设置",
      bio: "这个人很懒，什么都没写~",
    };
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("is_logged_in");
    localStorage.removeItem("user_info");
  }

  // ==================== 标记登录成功（供 Login 页面调用） ====================
  function setLoginSuccess(token, refresh, info = {}) {
    accessToken.value = token;
    if (refresh) refreshToken.value = refresh;
    isLoggedIn.value = true;
    if (Object.keys(info).length) {
      userInfo.value = { ...userInfo.value, ...info };
    }
    persistToStorage();
  }

  // ==================== 更新 Token ====================
  function updateAccessToken(token) {
    accessToken.value = token;
    localStorage.setItem("access_token", token);
  }

  // ==================== 从服务端同步用户信息 ====================
  async function syncProfileFromServer() {
    try {
      const res = await userAPI.getSettings(userInfo.value.username);
      if (res.data?.code === 0 && res.data?.data) {
        const data = res.data.data;
        if (data.username) userInfo.value.username = data.username;
        if (data.email) userInfo.value.email = data.email;
        if (data.avatar) userInfo.value.avatar = data.avatar;
        if (data.phone) userInfo.value.phone = data.phone;
        if (data.gender) userInfo.value.gender = data.gender;
        if (data.birthday) userInfo.value.birthday = data.birthday;
        if (data.bio) userInfo.value.bio = data.bio;
        persistToStorage();
      }
    } catch (e) {
      console.warn("同步用户信息失败:", e);
    }
  }

  return {
    // 状态
    isLoggedIn,
    accessToken,
    refreshToken,
    userInfo,
    // 计算属性
    username,
    avatar,
    // 方法
    initFromStorage,
    persistToStorage,
    loginFromUrlParams,
    setUserInfo,
    logout,
    setLoginSuccess,
    updateAccessToken,
    syncProfileFromServer,
  };
});
