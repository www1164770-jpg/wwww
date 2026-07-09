import axios from "axios";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000/api";

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

export function unwrapResponse(response) {
  if (Array.isArray(response)) return response;
  const payload = response?.data;
  if (payload?.data !== undefined) return payload.data;
  if (payload?.items !== undefined) return payload.items;
  return payload;
}

export function unwrapList(response) {
  if (Array.isArray(response)) return response;
  const payload = response?.data;
  const data = payload?.data ?? payload;
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.list)) return data.list;
  if (Array.isArray(data?.rows)) return data.rows;
  return [];
}

export function normalizeUrl(url) {
  const value = String(url || "").trim();
  if (!value) return "";
  if (/^https?:\/\//i.test(value)) return value;
  return `https://${value}`;
}

export function getDomain(url) {
  try {
    return new URL(normalizeUrl(url)).hostname;
  } catch {
    return "";
  }
}

export function getFaviconUrl(site = {}) {
  if (site.logo_url) return site.logo_url;
  const domain = getDomain(site.url);
  if (domain) {
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
  }
  return "";
}

export const CATEGORY_FALLBACK_SITES = {
  AI工具: [
    {
      name: "ChatGPT",
      url: "https://chat.openai.com",
      summary: "AI 对话与创作助手",
    },
    {
      name: "Claude",
      url: "https://claude.ai",
      summary: "长文本理解与 AI 助手",
    },
    {
      name: "Gemini",
      url: "https://gemini.google.com",
      summary: "Google AI 助手",
    },
    {
      name: "Perplexity",
      url: "https://www.perplexity.ai",
      summary: "AI 搜索与问答工具",
    },
  ],
  编程开发: [
    {
      name: "GitHub",
      url: "https://github.com",
      summary: "代码托管与开源协作平台",
    },
    {
      name: "MDN Web Docs",
      url: "https://developer.mozilla.org",
      summary: "Web 开发文档",
    },
    {
      name: "Vue 官方文档",
      url: "https://vuejs.org",
      summary: "Vue 前端框架文档",
    },
    {
      name: "LeetCode",
      url: "https://leetcode.cn",
      summary: "编程算法练习平台",
    },
  ],
  设计资源: [
    {
      name: "Figma",
      url: "https://www.figma.com",
      summary: "在线 UI 设计协作工具",
    },
    {
      name: "Canva",
      url: "https://www.canva.com",
      summary: "在线设计与模板工具",
    },
    { name: "Iconfont", url: "https://www.iconfont.cn", summary: "图标素材库" },
    {
      name: "Unsplash",
      url: "https://unsplash.com",
      summary: "高质量免费图片素材",
    },
  ],
  效率办公: [
    {
      name: "Notion",
      url: "https://www.notion.so",
      summary: "知识管理与协作工具",
    },
    {
      name: "飞书",
      url: "https://www.feishu.cn",
      summary: "团队协作与办公平台",
    },
    {
      name: "ProcessOn",
      url: "https://www.processon.com",
      summary: "流程图与思维导图工具",
    },
    { name: "Trello", url: "https://trello.com", summary: "任务看板管理工具" },
  ],
  学习成长: [
    {
      name: "Bilibili 学习区",
      url: "https://www.bilibili.com",
      summary: "视频学习内容平台",
    },
    {
      name: "Coursera",
      url: "https://www.coursera.org",
      summary: "在线课程学习平台",
    },
    {
      name: "Khan Academy",
      url: "https://www.khanacademy.org",
      summary: "免费教育学习平台",
    },
    {
      name: "中国大学 MOOC",
      url: "https://www.icourse163.org",
      summary: "高校在线课程平台",
    },
  ],
  数据分析: [
    {
      name: "Kaggle",
      url: "https://www.kaggle.com",
      summary: "数据科学竞赛与数据集平台",
    },
    {
      name: "Tableau",
      url: "https://www.tableau.com",
      summary: "商业智能可视化工具",
    },
    {
      name: "Power BI",
      url: "https://powerbi.microsoft.com",
      summary: "微软数据分析平台",
    },
    {
      name: "Jupyter",
      url: "https://jupyter.org",
      summary: "交互式数据分析环境",
    },
  ],
  产品运营: [
    {
      name: "Notion",
      url: "https://www.notion.so",
      summary: "产品文档与知识管理",
    },
    {
      name: "ProcessOn",
      url: "https://www.processon.com",
      summary: "流程图和原型思路整理",
    },
    { name: "飞书", url: "https://www.feishu.cn", summary: "团队协作文档平台" },
    {
      name: "Canva",
      url: "https://www.canva.com",
      summary: "运营视觉设计工具",
    },
  ],
  原型设计: [
    {
      name: "Figma",
      url: "https://www.figma.com",
      summary: "产品原型与 UI 设计",
    },
    { name: "墨刀", url: "https://modao.cc", summary: "在线原型设计协作工具" },
    {
      name: "ProcessOn",
      url: "https://www.processon.com",
      summary: "流程图与产品结构设计",
    },
    {
      name: "Canva",
      url: "https://www.canva.com",
      summary: "设计模板与视觉表达",
    },
  ],
};

export function getCategoryFallbackKey(categoryOrName) {
  const name = String(categoryOrName?.name || categoryOrName || "");
  if (CATEGORY_FALLBACK_SITES[name]) return name;
  if (name.includes("AI") || name.includes("智能")) return "AI工具";
  if (name.includes("编程") || name.includes("开发")) return "编程开发";
  if (name.includes("原型")) return "原型设计";
  if (name.includes("设计") || name.includes("素材")) return "设计资源";
  if (name.includes("办公") || name.includes("效率")) return "效率办公";
  if (name.includes("学习") || name.includes("成长") || name.includes("教育")) {
    return "学习成长";
  }
  if (name.includes("数据") || name.includes("分析")) return "数据分析";
  if (name.includes("产品") || name.includes("运营")) return "产品运营";
  return "";
}

export function getCategoryFallbackSites(categoryOrName) {
  const key = getCategoryFallbackKey(categoryOrName);
  return (key ? CATEGORY_FALLBACK_SITES[key] || [] : []).map((site) => ({
    ...site,
    id: `fallback-${key}-${site.name}`,
    category_name: key,
    external_only: true,
  }));
}

export function getTextLogo(site = {}) {
  const name = String(site.name || site.url || "站").trim();
  return Array.from(name)[0]?.toUpperCase() || "站";
}

function readPayload(response) {
  return unwrapResponse(response) ?? {};
}

function firstDefined(...values) {
  return values.find((value) => value !== undefined && value !== null);
}

function parseBoolean(value) {
  return value === true || value === 1 || value === "1" || value === "true";
}

export function storeUserSessionFromPayload(payload = {}, fallback = {}) {
  const root = payload?.data && payload?.status ? payload.data : payload || {};
  const nested = root?.data || {};
  const user = firstDefined(
    nested.user,
    root.user,
    nested.user_info,
    root.user_info,
    nested.username || nested.email ? nested : undefined,
    fallback.user,
  );
  const token = firstDefined(
    fallback.token,
    root.token,
    nested.token,
    root.access_token,
    nested.access_token,
  );
  const refreshToken = firstDefined(
    fallback.refreshToken,
    root.refresh_token,
    nested.refresh_token,
    "",
  );
  const userRole = firstDefined(
    root.user_role,
    nested.user_role,
    user?.role,
    fallback.userRole,
    "user",
  );
  const questionnaireCompleted = parseBoolean(
    firstDefined(
      root.questionnaire_completed,
      nested.questionnaire_completed,
      root.questionnaireCompleted,
      nested.questionnaireCompleted,
      user?.questionnaire_completed,
      user?.questionnaireCompleted,
      fallback.questionnaireCompleted,
    ),
  );

  if (token) {
    localStorage.setItem("token", token);
    localStorage.setItem("access_token", token);
  }
  localStorage.setItem("refresh_token", refreshToken || "");
  if (user) {
    localStorage.setItem("user", JSON.stringify(user));
    localStorage.setItem("user_info", JSON.stringify(user));
  }
  localStorage.setItem("user_role", userRole);
  localStorage.setItem(
    "questionnaire_completed",
    questionnaireCompleted ? "true" : "false",
  );
  localStorage.setItem("is_logged_in", "true");

  return { token, refreshToken, user, userRole, questionnaireCompleted };
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
  getQuestionnaires: () => api.get("/admin/questionnaires"),
  saveQuestionnaireConfig: (data) => api.post("/admin/questionnaires", data),
  getRecommendRules: () => api.get("/admin/recommend-rules"),
  saveRecommendRules: (data) => api.post("/admin/recommend-rules", data),
  getSettings: () => api.get("/admin/settings"),
  saveSettings: (data) => api.post("/admin/settings", data),
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
