import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

export function unwrapResponse(response) {
  const payload = response?.data;
  if (payload?.data !== undefined) return payload.data;
  if (payload?.items !== undefined) return payload.items;
  return payload;
}

export function unwrapList(response) {
  const payload = response?.data;
  const data = payload?.data ?? payload;
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.list)) return data.list;
  if (Array.isArray(data?.rows)) return data.rows;
  return [];
}

function readPayload(response) {
  return unwrapResponse(response) ?? {};
}

function clearAuthAndRedirect() {
  localStorage.removeItem("token");
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
  localStorage.removeItem("user_info");
  localStorage.removeItem("user_role");
  localStorage.removeItem("questionnaire_completed");
  localStorage.removeItem("is_logged_in");
  if (!["/login", "/authing/callback"].includes(window.location.pathname)) {
    window.location.href = "/login";
  }
}

function isValidToken(token) {
  const value = String(token || "");
  if (value.length <= 20) return false;
  return !value.includes(".") || value.split(".").length === 3;
}

api.interceptors.request.use((config) => {
  const token =
    localStorage.getItem("token") || localStorage.getItem("access_token");
  if (isValidToken(token)) {
    config.headers.Authorization = `Bearer ${token}`;
  } else {
    localStorage.removeItem("token");
    localStorage.removeItem("access_token");
    if (config.headers) {
      delete config.headers.Authorization;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 429) {
      const retryAfter = error.response.data?.retry_after;
      const message = retryAfter
        ? `请求过于频繁，请 ${retryAfter} 秒后再试`
        : "请求过于频繁，请稍后再试";
      error.response.data = {
        ...error.response.data,
        message,
        msg: message,
      };
      error.message = message;
      return Promise.reject(error);
    }

    if (error.response?.status === 401) {
      clearAuthAndRedirect();
    }
    return Promise.reject(error);
  },
);

export const authAPI = {
  sendCode: (email) => api.post("/auth/send-code", { email }),
  register: (data) => api.post("/auth/register", data),
  login: (account, password) => api.post("/auth/login", { account, password }),
  logout: () => api.post("/auth/logout"),
  refresh: () => api.post("/auth/refresh"),
  refreshToken: () => api.post("/auth/refresh"),
  sendResetCode: (email) => api.post("/auth/send-reset-code", { email }),
  verifyResetCode: (email, code) =>
    api.post("/auth/verify-reset-code", { email, code }),
  resetPassword: (email, code, newPassword) =>
    api.post("/auth/reset-password", {
      email,
      code,
      new_password: newPassword,
    }),
  githubLoginUrl: `${API_BASE_URL}/login/github`,
};

export const userAPI = {
  getProfile: () => api.get("/user/profile"),
  updateProfile: (data) => api.put("/user/profile", data),
  changePassword: (oldPassword, newPassword) =>
    api.put("/user/password", {
      old_password: oldPassword,
      new_password: newPassword,
    }),
  getProfileTags: () => api.get("/user/profile-tags"),
  getStats: (username) => api.get("/user/stats", { params: { username } }),
  getDevices: () => api.get("/user/devices"),
  getHistory: () => api.get("/user/history"),
  clearHistory: () => api.post("/user/history/clear"),
  getContents: (status = "pending") =>
    api.get("/user/contents", { params: { status } }),
  deleteContent: (id) => api.post("/user/contents/delete", { id }),
  deleteAccount: (password) => api.post("/user/delete-account", { password }),
  syncSettings: (settings) => api.post("/user/sync", settings),
  getSettings: (username) =>
    api.get("/user/settings", { params: { username } }),
  submitSurvey: (interests) => api.post("/user/survey", { interests }),
};

export const questionnaireAPI = {
  get: () => api.get("/questionnaire"),
  submit: (data) => api.post("/questionnaire/submit", data),
  getMyQuestionnaire: () => api.get("/questionnaire/my"),
  getProfileTags: () => api.get("/user/profile-tags"),
};

export const siteAPI = {
  getSites: (params = {}) => api.get("/sites", { params }),
  getSite: (id) => api.get(`/sites/${id}`),
  getRandom: (params = {}) => api.get("/sites/random", { params }),
  getHot: (params = {}) => api.get("/sites/hot", { params }),
  getLatest: (params = {}) => api.get("/sites/latest", { params }),
  getRecommend: (params = {}) => api.get("/sites/recommend", { params }),
  recordClick: (id) => api.post(`/sites/${id}/click`),
  getSimilar: (id) => api.get(`/sites/${id}/similar`),
};

export const favoriteAPI = {
  getFavorites: () => api.get("/favorites"),
  addFavorite: (siteId, note = "") =>
    api.post(`/sites/${siteId}/favorite`, { note }),
  removeFavorite: (siteId) => api.delete(`/sites/${siteId}/favorite`),
  updateNote: (siteId, note = "") =>
    api.put(`/sites/${siteId}/favorite`, { note }),
};

export const searchAPI = {
  search: (params = {}) => api.get("/search", { params }),
  suggest: (q) => api.get("/search/suggest", { params: { q } }),
  hotKeywords: () => api.get("/search/hot-keywords"),
};

export const categoryAPI = {
  getCategories: () => api.get("/categories"),
  getCategory: (id) => api.get(`/categories/${id}`),
};

export const tagAPI = {
  getTags: () => api.get("/tags"),
};

export const adminAPI = {
  getDashboard: () => api.get("/admin/dashboard"),
  getUsers: (params = {}) => api.get("/admin/users", { params }),
  updateUserStatus: (id, status) =>
    api.put(`/admin/users/${id}/status`, { status }),
  getSites: (params = {}) => api.get("/admin/sites", { params }),
  createSite: (data) => api.post("/admin/sites", data),
  updateSite: (id, data) => api.put(`/admin/sites/${id}`, data),
  deleteSite: (id) => api.delete(`/admin/sites/${id}`),
  getCategories: () => api.get("/admin/categories"),
  createCategory: (data) => api.post("/admin/categories", data),
  updateCategory: (id, data) => api.put(`/admin/categories/${id}`, data),
  deleteCategory: (id) => api.delete(`/admin/categories/${id}`),
  getTags: () => api.get("/admin/tags"),
  createTag: (data) => api.post("/admin/tags", data),
  updateTag: (id, data) => api.put(`/admin/tags/${id}`, data),
  deleteTag: (id) => api.delete(`/admin/tags/${id}`),
  getComments: (params = {}) => api.get("/admin/comments", { params }),
  reviewComment: (id, action) =>
    api.post(`/admin/comments/${id}/review`, { action }),
  deleteComment: (id) => api.delete(`/admin/comments/${id}`),
  getPendingSites: () => api.get("/admin/pending_sites"),
  crawlHN: () => api.post("/admin/crawl_hn"),
  reviewSite: (id, action, reason = "") =>
    api.post("/admin/review_site", { id, action, reason }),
  getStatsOverview: () => api.get("/admin/stats/overview"),
  toggleUserBan: (userId, banned) =>
    api.post("/admin/user/ban", { user_id: userId, banned }),
  getContentAuditList: (status = "pending", page = 1) =>
    api.get("/admin/content-audit", { params: { status, page } }),
  reviewContent: (id, action, reason = "") =>
    api.post("/admin/review-content", { id, action, reason }),
};

export const commentAPI = {
  getComments: (siteId) => api.get(`/sites/${siteId}/comments`),
  addComment: (siteId, data) => api.post(`/sites/${siteId}/comments`, data),
  deleteComment: (commentId) => api.delete(`/comments/${commentId}`),
};

export const navAPI = {
  getNavData: () => api.get("/nav-data"),
  recordClick: (id) => siteAPI.recordClick(id),
  getFavorites: () => favoriteAPI.getFavorites(),
  addFavorite: (websiteId) => favoriteAPI.addFavorite(websiteId),
  removeFavorite: (websiteId) => favoriteAPI.removeFavorite(websiteId),
  suggestSite: (data) => api.post("/suggest-site", data),
  search: (query, options = {}) => searchAPI.search({ q: query, ...options }),
};

export const feedAPI = {
  getGrowthRanking: () => api.get("/ranking/growth"),
  getHotRanking: () => api.get("/ranking/hot"),
  getNews: (prof) => api.get("/news", { params: { prof } }),
  getRecommendations: () => siteAPI.getRecommend(),
  getArticle: (id) => api.get(`/article/${id}`),
  likeArticle: (id) => api.post(`/article/${id}/like`),
  postComment: (articleId, content, parentId = null) =>
    api.post(`/article/${articleId}/comment`, { content, parent_id: parentId }),
  getComments: (articleId, page = 1) =>
    api.get(`/article/${articleId}/comments`, { params: { page } }),
};

export const securityAPI = {
  sendEmailCode: (email) => api.post("/security/send-email-code", { email }),
  sendSmsCode: (phone) => api.post("/security/send-sms-code", { phone }),
  bindEmail: (email, code) => api.post("/security/bind-email", { email, code }),
  bindPhone: (phone, code) => api.post("/security/bind-phone", { phone, code }),
};

export const notificationAPI = {
  getUnreadCount: () => api.get("/notifications/unread-count"),
  getNotifications: (page = 1) =>
    api.get("/notifications", { params: { page } }),
  markRead: (notificationId) =>
    api.post(`/notifications/${notificationId}/read`),
  markAllRead: () => api.post("/notifications/read-all"),
};

export default api;
