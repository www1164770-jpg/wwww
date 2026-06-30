import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

function readPayload(response) {
  return response?.data?.data ?? response?.data ?? {};
}

function clearAuthAndRedirect() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user_info");
  localStorage.removeItem("user_role");
  localStorage.removeItem("questionnaire_completed");
  localStorage.removeItem("is_logged_in");
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

let isRefreshing = false;
let pendingRequests = [];

function resolvePending(token) {
  pendingRequests.forEach(({ resolve }) => resolve(token));
  pendingRequests = [];
}

function rejectPending(error) {
  pendingRequests.forEach(({ reject }) => reject(error));
  pendingRequests = [];
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        clearAuthAndRedirect();
        return Promise.reject(error);
      }
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingRequests.push({
            resolve: (token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(api(originalRequest));
            },
            reject,
          });
        });
      }
      originalRequest._retry = true;
      isRefreshing = true;
      try {
        const response = await axios.post(
          `${API_BASE_URL}/auth/refresh`,
          null,
          {
            headers: { Authorization: `Bearer ${refreshToken}` },
          },
        );
        const payload = readPayload(response);
        const token = payload.access_token || response.data.access_token;
        localStorage.setItem("access_token", token);
        resolvePending(token);
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      } catch (refreshError) {
        rejectPending(refreshError);
        clearAuthAndRedirect();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
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
  getProfileTags: () => api.get("/user/profile-tags"),
};

export const siteAPI = {
  getSites: (params = {}) => api.get("/sites", { params }),
  getSite: (id) => api.get(`/sites/${id}`),
  getHot: (params = {}) => api.get("/sites/hot", { params }),
  getLatest: (params = {}) => api.get("/sites/latest", { params }),
  getRecommend: (params = {}) => api.get("/sites/recommend", { params }),
  recordClick: (id) => api.post(`/sites/${id}/click`),
};

export const favoriteAPI = {
  getFavorites: () => api.get("/favorites"),
  addFavorite: (siteId, note = "") =>
    api.post(`/sites/${siteId}/favorite`, { note }),
  removeFavorite: (siteId) => api.delete(`/sites/${siteId}/favorite`),
};

export const searchAPI = {
  search: (params = {}) => api.get("/search", { params }),
  suggest: (q) => api.get("/search/suggest", { params: { q } }),
  hotKeywords: () => api.get("/search/hot-keywords"),
};

export const categoryAPI = {
  getCategories: () => api.get("/categories"),
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
