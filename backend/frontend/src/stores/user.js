/**
 * 用户全局状态管理
 *
 * Pinia 只负责把统一 auth.js 认证状态映射到组件，localStorage 的读写和
 * 清理全部由 auth.js 完成，避免各页面维护不同版本的认证字段列表。
 */

import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { userAPI } from "../utils/api";
import { questionnaireAPI, unwrapResponse } from "../utils/api";
import {
  addAuthStateListener,
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  getStoredQuestionnaireCompleted,
  getStoredUserInfo,
  getStoredUserRole,
  saveAuthSession,
  setQuestionnaireCompleted as persistQuestionnaireCompleted,
} from "../utils/auth";

const DEFAULT_USER_INFO = Object.freeze({
  username: "",
  avatar: "",
  email: "未绑定邮箱",
  phone: "",
  gender: "保密",
  birthday: "未设置",
  bio: "这个人很懒，什么都没写~",
});

export const useUserStore = defineStore("user", () => {
  const isLoggedIn = ref(false);
  const accessToken = ref(null);
  const refreshToken = ref(null);
  const userRole = ref("user");
  const questionnaireCompleted = ref(false);
  const userInfo = ref({ ...DEFAULT_USER_INFO });
  const isHydrated = ref(false);
  const questionnaireStatus = ref(null);
  const questionnaireStatusLoaded = ref(false);
  const statusLoadedForUserId = ref("");
  const questionnaireModalVisible = ref(false);
  const questionnaireRevision = ref(0);
  let questionnaireStatusRequest = null;

  const username = computed(() => userInfo.value.username);
  const avatar = computed(
    () =>
      userInfo.value.avatar ||
      "https://api.dicebear.com/7.x/avataaars/svg?seed=fallback",
  );

  function syncFromStorage() {
    accessToken.value = getAccessToken();
    refreshToken.value = getRefreshToken();
    isLoggedIn.value = Boolean(accessToken.value);
    userRole.value = getStoredUserRole();
    questionnaireCompleted.value = getStoredQuestionnaireCompleted();
    userInfo.value = { ...DEFAULT_USER_INFO, ...getStoredUserInfo() };
    isHydrated.value = true;
  }

  function initFromStorage() {
    syncFromStorage();
  }

  async function ensureHydrated() {
    if (!isHydrated.value) syncFromStorage();
    return true;
  }

  function persistToStorage() {
    if (!accessToken.value) {
      clearAuthSession();
      syncFromStorage();
      return;
    }

    saveAuthSession({
      access_token: accessToken.value,
      refresh_token: refreshToken.value || "",
      user_info: userInfo.value,
      user_role: userRole.value,
      questionnaire_completed: questionnaireCompleted.value,
    });
    syncFromStorage();
  }

  function setUserInfo(info = {}) {
    userInfo.value = { ...userInfo.value, ...info };
    persistToStorage();
  }

  function resetState() {
    accessToken.value = null;
    refreshToken.value = null;
    isLoggedIn.value = false;
    userRole.value = "user";
    questionnaireCompleted.value = false;
    userInfo.value = { ...DEFAULT_USER_INFO };
    resetQuestionnaireState();
  }

  function resetQuestionnaireState() {
    questionnaireStatus.value = null;
    questionnaireStatusLoaded.value = false;
    statusLoadedForUserId.value = "";
    questionnaireModalVisible.value = false;
    questionnaireStatusRequest = null;
  }

  function getQuestionnaireUserId() {
    return String(
      userInfo.value?.id || userInfo.value?.user_id || userInfo.value?.username || "",
    ).trim();
  }

  async function checkQuestionnaireStatus({ open = true, force = false } = {}) {
    if (!isLoggedIn.value || !getAccessToken()) {
      resetQuestionnaireState();
      return null;
    }
    const userId = getQuestionnaireUserId();
    if (!userId) return null;
    if (!force && statusLoadedForUserId.value === userId && questionnaireStatusLoaded.value) {
      return questionnaireStatus.value;
    }
    if (questionnaireStatusRequest && !force) return questionnaireStatusRequest;
    statusLoadedForUserId.value = userId;
    questionnaireStatusRequest = questionnaireAPI
      .status()
      .then((response) => {
        const payload = unwrapResponse(response) || {};
        questionnaireStatus.value = payload;
        questionnaireStatusLoaded.value = true;
        updateQuestionnaireCompleted(Boolean(payload.completed), { silentStatus: true });
        if (open && !payload.completed) questionnaireModalVisible.value = true;
        return payload;
      })
      .catch((requestError) => {
        questionnaireStatusLoaded.value = true;
        console.error("[questionnaire] status request failed", requestError);
        return null;
      })
      .finally(() => {
        questionnaireStatusRequest = null;
      });
    return questionnaireStatusRequest;
  }

  function dismissQuestionnaireModal() {
    questionnaireModalVisible.value = false;
  }

  function logout() {
    clearAuthSession();
    resetState();
  }

  function setLoginSuccess(tokenOrSession, refresh, info = {}) {
    const session =
      tokenOrSession && typeof tokenOrSession === "object"
        ? tokenOrSession
        : {
            access_token: tokenOrSession,
            refresh_token: refresh,
            user_info: info.user_info || info,
            user_role: info.user_role || info.role,
            questionnaire_completed:
              info.questionnaire_completed ?? info.questionnaireCompleted,
          };

    saveAuthSession(session);
    syncFromStorage();
  }

  function updateAccessToken(token) {
    saveAuthSession({ access_token: token });
    syncFromStorage();
  }

  function updateQuestionnaireCompleted(value, { silentStatus = false } = {}) {
    persistQuestionnaireCompleted(value);
    questionnaireCompleted.value =
      value === true || value === "true" || value === 1;
    if (questionnaireCompleted.value) questionnaireModalVisible.value = false;
    if (!silentStatus) {
      questionnaireStatus.value = {
        ...(questionnaireStatus.value || {}),
        completed: questionnaireCompleted.value,
        questionnaire_version: 3,
        latest_completed_version: questionnaireCompleted.value ? 3 : null,
      };
      questionnaireStatusLoaded.value = true;
      questionnaireRevision.value += 1;
    }
  }

  async function syncProfileFromServer() {
    try {
      const res = await userAPI.getSettings(userInfo.value.username);
      if (res.data?.code === 0 && res.data?.data) {
        const data = res.data.data;
        userInfo.value = {
          ...userInfo.value,
          ...Object.fromEntries(
            [
              "username",
              "email",
              "avatar",
              "phone",
              "gender",
              "birthday",
              "bio",
            ]
              .filter((key) => data[key])
              .map((key) => [key, data[key]]),
          ),
        };
        persistToStorage();
      }
    } catch (error) {
      console.warn("同步用户信息失败:", error);
    }
  }

  syncFromStorage();
  addAuthStateListener(syncFromStorage);

  return {
    isLoggedIn,
    accessToken,
    refreshToken,
    userRole,
    questionnaireCompleted,
    isHydrated,
    userInfo,
    username,
    avatar,
    initFromStorage,
    ensureHydrated,
    persistToStorage,
    setUserInfo,
    logout,
    setLoginSuccess,
    updateAccessToken,
    updateQuestionnaireCompleted,
    questionnaireStatus,
    questionnaireStatusLoaded,
    statusLoadedForUserId,
    questionnaireModalVisible,
    questionnaireRevision,
    checkQuestionnaireStatus,
    dismissQuestionnaireModal,
    resetQuestionnaireState,
    syncProfileFromServer,
  };
});
