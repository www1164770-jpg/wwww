import axios from "axios";
import {
  clearAuthSession,
  applyAuthRequestHeaders,
  getAccessToken,
  getRefreshToken,
  isValidAuthToken,
  normalizeAuthSession,
  saveAuthSession,
} from "./auth";
import { resolveApiBaseURL } from "./apiBase";

const DEFAULT_API_BASE_URL = "/api";

export const API_TIMEOUT_MS = 15000;
export const FAVORITE_MUTATION_TIMEOUT_MS = 10000;
export const AUTH_REQUEST_TIMEOUT_MS = 15000;
export const VERIFICATION_REQUEST_TIMEOUT_MS = 30000;

export const API_BASE_URL = resolveApiBaseURL(
  import.meta.env,
  DEFAULT_API_BASE_URL,
);

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
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
  const payload = response?.data ?? response;
  const candidates = [
    payload,
    payload?.data,
    payload?.items,
    payload?.sites,
    payload?.results,
    payload?.list,
    payload?.rows,
    payload?.data?.items,
    payload?.data?.sites,
    payload?.data?.results,
    payload?.data?.list,
    payload?.data?.rows,
  ];
  return candidates.find(Array.isArray) || [];
}

export function normalizeStringArray(value) {
  if (Array.isArray(value)) {
    return value
      .filter(Boolean)
      .map((item) => String(item).trim())
      .filter(Boolean);
  }

  if (typeof value === "string" && value.trim()) {
    return value
      .split(/[,，、|]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  return [];
}

function isUsableSiteSummary(value) {
  const text = String(value || "").trim();
  return Boolean(text) && !/^(?:https?:\/\/|www\.)/i.test(text);
}

export function normalizeWebsite(site = {}) {
  const relatedCategory = site.category;
  const categoryName =
    typeof relatedCategory === "object"
      ? relatedCategory?.name
      : relatedCategory;
  const id =
    site.id ?? site.site_id ?? site.siteId ?? site.url ?? site.name ?? "";
  const name = site.name ?? site.title ?? site.site_name ?? "未命名网站";
  const url = site.url ?? site.website_url ?? site.href ?? site.link ?? "";
  const normalizedId = String(id);
  const renderKey = String(site.renderKey ?? `${normalizedId}::${url || name}`);
  const shortDescription =
    [
      site.shortDescription,
      site.short_description,
      site.summary,
      site.intro,
      site.site_description,
      site.description,
    ]
      .find((value) => isUsableSiteSummary(value))
      ?.trim() || "";

  return {
    ...site,
    id: normalizedId,
    renderKey,
    name,
    url,
    category_code:
      site.category_code ?? site.categoryCode ?? site.category_code_id ?? "",
    categoryCode:
      site.categoryCode ?? site.category_code ?? site.category_code_id ?? "",
    category_name:
      site.category_name ?? site.categoryName ?? categoryName ?? "未分类",
    categoryName:
      site.categoryName ?? site.category_name ?? categoryName ?? "未分类",
    shortDescription,
    summary: shortDescription,
    tags: normalizeStringArray(site.tags),
    occupations: normalizeStringArray(site.occupations),
    logo_url: site.logo_url ?? site.logo ?? site.icon ?? site.favicon ?? "",
    logoUrl:
      site.logoUrl ?? site.logo_url ?? site.logo ?? site.icon ?? site.favicon ?? "",
  };
}

const CAREER_SITE_SUMMARY_FALLBACKS = Object.freeze({
  github: "代码托管、开源协作与项目交付平台。",
  "mdn web docs": "面向 Web 开发者的权威技术文档网站。",
  mdn: "面向 Web 开发者的权威技术文档网站。",
  "stack overflow": "开发者常用的技术问答与问题检索社区。",
  kaggle: "提供数据集、竞赛和练习项目的数据科学平台。",
  "hugging face": "聚合模型、数据集与 AI 开发资源的平台。",
  figma: "支持协作设计与原型制作的产品设计工具。",
  coursera: "提供系统课程学习与职业提升内容的在线教育平台。",
  "power bi": "用于数据分析、报表制作与可视化展示的工具平台。",
  leetcode: "用于算法练习、面试准备和编程能力提升的平台。",
  behance: "设计作品展示与创意灵感发现平台。",
});

const CAREER_CATEGORY_SUMMARY_FALLBACKS = Object.freeze({
  前端开发: "面向前端开发学习与项目实践的工具和资源。",
  后端开发: "面向后端服务、API 开发与工程实践的资源。",
  数据分析: "用于数据处理、分析建模和可视化实践的资源。",
  技术研发: "面向技术研发、代码实践与项目协作的资源。",
  教育与内容: "用于学习、知识整理和内容创作的资源。",
  产品与设计: "支持产品规划、界面设计和协作交付的资源。",
  设计资源: "用于视觉设计、灵感收集和素材制作的资源。",
  学习资源: "帮助学习、练习和查找专业资料的资源。",
});

export function normalizeWebsiteList(response) {
  return unwrapList(response).filter(Boolean).map(normalizeWebsite);
}

export function generateFallbackSummary(site = {}) {
  const name = normalizeSiteName(site.name);
  const knownSummary = CAREER_SITE_SUMMARY_FALLBACKS[name];
  if (knownSummary) return knownSummary;

  const category = String(
    site.category_name || site.categoryName || site.category || "",
  ).trim();
  const categorySummary = CAREER_CATEGORY_SUMMARY_FALLBACKS[category];
  if (categorySummary) return `${site.name || "该网站"}：${categorySummary}`;

  const tags = normalizeStringArray(site.tags).slice(0, 2);
  if (tags.length) {
    return `${site.name || "该网站"}：围绕${tags.join("、")}提供实用工具与参考资源。`;
  }

  return `${site.name || "该网站"}：提供适合当前职业方向的学习与实践资源。`;
}

export function normalizeCareerSite(site = {}) {
  const sourceSummary = getSiteSummary(site);
  const normalized = normalizeWebsite(site);
  const summary =
    sourceSummary ||
    getSiteSummary(normalized) ||
    generateFallbackSummary(normalized);
  const careerCodes = normalizeStringArray(
    site.careerCodes ||
      site.career_codes ||
      site.occupationCodes ||
      site.occupations,
  );
  const description = isUsableSiteSummary(site.description)
    ? site.description.trim()
    : summary;

  return {
    ...normalized,
    summary,
    shortDescription: summary,
    description,
    logoUrl: normalized.logo_url,
    categoryName: normalized.category_name,
    careerCodes,
  };
}

export function normalizeCareerSiteList(response) {
  return unwrapList(response).filter(Boolean).map(normalizeCareerSite);
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

export function normalizeSiteKey(site = {}) {
  try {
    const hostname = new URL(normalizeUrl(site?.url)).hostname
      .toLowerCase()
      .replace(/^www\./, "");
    if (hostname) return `host:${hostname}`;
  } catch {
    // Fall back to the normalized name below.
  }

  if (site?.id !== undefined && site?.id !== null && String(site.id).trim()) {
    return `id:${String(site.id).trim()}`;
  }

  const name = normalizeSiteName(site?.name);
  return name ? `name:${name}` : "";
}

function normalizeLogoUrl(value) {
  const source = String(value || "").trim();
  if (!source) return "";
  // Keep same-origin assets, but reject protocol-relative URLs: on an HTTPS
  // page they could resolve to an unexpected insecure or third-party source.
  if (source.startsWith("/") && !source.startsWith("//")) return source;

  try {
    const parsed = new URL(source);
    return parsed.protocol === "https:" ? parsed.href : "";
  } catch {
    return "";
  }
}

export function resolveSiteLogo(site = {}) {
  const logoUrl = normalizeLogoUrl(site.logo_url);
  if (logoUrl) return logoUrl;

  const domain = getDomain(site.url);
  if (domain) {
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
  }
  return "";
}

export function getFaviconUrl(site = {}) {
  return resolveSiteLogo(site);
}

export const SITE_DESCRIPTION_FALLBACKS = Object.freeze({
  github: "代码托管与协作开发平台",
  "mdn web docs": "面向 Web 开发者的权威技术文档",
  mdn: "面向 Web 开发者的权威技术文档",
  "stack overflow": "开发者问答与知识社区",
  figma: "协作式界面设计与原型工具",
  vercel: "面向前端团队的云端部署平台",
  chatgpt: "通用型 AI 助手",
  midjourney: "AI 图像生成与创意工具",
  "hugging face": "开源模型、数据集与机器学习社区",
  notion: "笔记、知识库与团队协作工具",
  claude: "面向分析、写作与编程的 AI 助手",
});

export function normalizeSiteName(name) {
  return String(name || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

export function getSiteSummary(site = {}) {
  const values = [
    site.summary,
    site.description,
    site.slogan,
    site.shortDescription,
    site.short_description,
    site.intro,
    site.site_description,
    site.desc,
  ];
  const providedDescription = values.find((value) =>
    isUsableSiteSummary(value),
  );

  return (
    providedDescription?.trim() ||
    SITE_DESCRIPTION_FALLBACKS[normalizeSiteName(site.name)] ||
    generateFallbackSummary(site)
  );
}

export function getSiteDescription(site = {}) {
  return getSiteSummary(site);
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

export function storeUserSessionFromPayload(payload = {}, fallback = {}) {
  const session = saveAuthSession(payload, fallback);
  return {
    token: session.access_token,
    refreshToken: session.refresh_token,
    user: session.user_info,
    userRole: session.user_role,
    questionnaireCompleted: session.questionnaire_completed,
  };
}

function isAuthEndpoint(config = {}) {
  const url = String(config.url || "");
  return [
    "/auth/login",
    "/auth/register",
    "/auth/send-register-code",
    "/auth/send-reset-code",
    "/auth/verify-reset-code",
    "/auth/reset-password",
    "/auth/refresh",
    "/auth/logout",
  ].some((path) => url.includes(path));
}

function redirectToLogin() {
  if (
    typeof window === "undefined" ||
    ["/login"].includes(window.location.pathname)
  ) {
    return;
  }

  const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  const target = `/login?redirect=${encodeURIComponent(currentPath || "/")}`;
  if (typeof window.location.replace === "function") {
    window.location.replace(target);
  } else {
    window.location.href = target;
  }
}

let refreshPromise = null;
let authFailureHandled = false;

function invalidateAuthSession() {
  if (authFailureHandled) return;
  authFailureHandled = true;
  clearAuthSession();
  redirectToLogin();
}

function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return Promise.reject(new Error("Refresh Token 不存在"));
  }

  if (!refreshPromise) {
    refreshPromise = api
      .post(
        "/auth/refresh",
        {},
        {
          skipAuth: true,
          headers: { Authorization: `Bearer ${refreshToken}` },
        },
      )
      .then((response) => {
        const session = normalizeAuthSession(response);
        if (!isValidAuthToken(session.access_token)) {
          throw new Error("Refresh 响应缺少有效 Access Token");
        }
        authFailureHandled = false;
        saveAuthSession({ access_token: session.access_token });
        return session.access_token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

api.interceptors.request.use(applyAuthRequestHeaders);

api.interceptors.response.use(
  (response) => {
    if (getAccessToken()) authFailureHandled = false;
    return response;
  },
  async (error) => {
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

    if (error.response?.status !== 401) {
      return Promise.reject(error);
    }

    const originalConfig = error.config || {};
    if (originalConfig.skipAuth || isAuthEndpoint(originalConfig)) {
      return Promise.reject(error);
    }

    if (originalConfig._retry) {
      invalidateAuthSession();
      return Promise.reject(error);
    }

    originalConfig._retry = true;
    try {
      const newAccessToken = await refreshAccessToken();
      originalConfig.headers = originalConfig.headers || {};
      originalConfig.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalConfig);
    } catch (refreshError) {
      invalidateAuthSession();
      return Promise.reject(refreshError);
    }
  },
);

export const authAPI = {
  register: (data) =>
    api.post("/auth/register", data, { timeout: AUTH_REQUEST_TIMEOUT_MS }),
  sendRegisterCode: (data) =>
    api.post("/auth/send-register-code", data, {
      timeout: VERIFICATION_REQUEST_TIMEOUT_MS,
    }),
  login: (account, password) =>
    api.post(
      "/auth/login",
      { account: account.trim(), password },
      { timeout: AUTH_REQUEST_TIMEOUT_MS },
    ),
  logout: () => api.post("/auth/logout"),
  refresh: () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return Promise.reject(new Error("Refresh Token 不存在"));
    return api.post(
      "/auth/refresh",
      {},
      {
        skipAuth: true,
        headers: { Authorization: `Bearer ${refreshToken}` },
      },
    );
  },
  refreshToken: () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return Promise.reject(new Error("Refresh Token 不存在"));
    return api.post(
      "/auth/refresh",
      {},
      {
        skipAuth: true,
        headers: { Authorization: `Bearer ${refreshToken}` },
      },
    );
  },
  me: () => api.get("/auth/me"),
  sendResetCode: (email) =>
    api.post(
      "/auth/send-reset-code",
      { email: email.trim().toLowerCase() },
      { timeout: VERIFICATION_REQUEST_TIMEOUT_MS },
    ),
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

export const careerAPI = {
  getRecommendations: (config = {}) => api.get("/career/recommend", config),
};

export const siteAPI = {
  getSites: (params = {}, config = {}) =>
    api.get("/sites", { ...config, params }),
  getSite: (id) => api.get(`/sites/${id}`),
  getRandom: (params = {}, config = {}) =>
    api.get("/sites/random", { ...config, params }),
  getHot: (params = {}, config = {}) =>
    api.get("/sites/hot", { ...config, params }),
  getLatest: (params = {}, config = {}) =>
    api.get("/sites/latest", { ...config, params }),
  getRecommend: (params = {}, config = {}) =>
    api.get("/sites/recommend", { ...config, params }),
  recordClick: (id) => api.post(`/sites/${id}/click`),
  getSimilar: (id) => api.get(`/sites/${id}/similar`),
};

export const aiAPI = {
  recommendSites: (payload) => api.post("/ai/site-recommend", payload),
};

function getFavoriteTarget(siteOrId) {
  if (siteOrId && typeof siteOrId === "object") {
    const rawSiteId =
      siteOrId.siteId ?? siteOrId.site_id ?? siteOrId.id ?? "";
    const siteId = /^\d+$/.test(String(rawSiteId).trim())
      ? String(rawSiteId).trim()
      : "";
    const rawUrl =
      siteOrId.url ?? siteOrId.website_url ?? siteOrId.link ?? "";
    const rawFavoriteId =
      siteOrId.favoriteId ?? siteOrId.favorite_id ?? "";
    const favoriteId = /^\d+$/.test(String(rawFavoriteId).trim())
      ? String(rawFavoriteId).trim()
      : "";
    return { siteId, favoriteId, url: normalizeUrl(rawUrl) };
  }

  const value = String(siteOrId ?? "").trim();
  return {
    siteId: /^\d+$/.test(value) ? value : "",
    favoriteId: "",
    url: "",
  };
}

function favoriteMutationDiagnostic(operation, target, requestConfig, response, error) {
  const startedAt = requestConfig.startedAt;
  const responsePayload = response?.data;
  const errorPayload = error?.response?.data;
  return {
    operation,
    siteId: target.siteId || "",
    favoriteId: target.favoriteId || "",
    url: requestConfig.url,
    method: requestConfig.method,
    payload: requestConfig.payload ?? null,
    status: response?.status ?? error?.response?.status ?? null,
    durationMs: Math.max(0, Date.now() - startedAt),
    code:
      errorPayload?.code ??
      errorPayload?.error_code ??
      responsePayload?.code ??
      responsePayload?.data?.code ??
      "",
    response: responsePayload ?? errorPayload ?? null,
  };
}

async function runFavoriteMutation(operation, target, requestConfig, request) {
  const config = { ...requestConfig, startedAt: Date.now() };
  try {
    const response = await request(config);
    if (import.meta.env.DEV) {
      console.debug(
        "[Favorite sync completed]",
        favoriteMutationDiagnostic(operation, target, config, response, null),
      );
    }
    return response;
  } catch (error) {
    if (import.meta.env.DEV) {
      console.error("[Favorite sync failed]", favoriteMutationDiagnostic(operation, target, config, null, error));
    }
    throw error;
  }
}

function notifyFavoriteStateChange(siteOrId, favorited) {
  if (typeof window === "undefined") return;
  const { siteId, url } = getFavoriteTarget(siteOrId);
  window.dispatchEvent(
    new CustomEvent("favorite-state-changed", {
      detail: {
        siteId,
        url,
        site: siteOrId,
        favorited: Boolean(favorited),
      },
    }),
  );
}

export const favoriteAPI = {
  getFavorites: (config = {}) => api.get("/favorites", config),
  addFavorite: async (siteOrId, note = "") => {
    const target = getFavoriteTarget(siteOrId);
    const url = target.siteId
      ? `/sites/${target.siteId}/favorite`
      : "/favorites";
    const payload = target.siteId
      ? { note }
      : { url: target.url, note };
    const response = await runFavoriteMutation(
      "add",
      target,
      { url, method: "POST", timeout: FAVORITE_MUTATION_TIMEOUT_MS, payload },
      (config) => api.post(url, payload, { timeout: config.timeout }),
    );
    notifyFavoriteStateChange(siteOrId, true);
    return response;
  },
  removeFavorite: async (siteOrId) => {
    const target = getFavoriteTarget(siteOrId);
    const url = target.siteId ? `/sites/${target.siteId}/favorite` : "/favorites";
    const payload = target.siteId ? undefined : { url: target.url };
    const response = await runFavoriteMutation(
      "remove",
      target,
      {
        url,
        method: "DELETE",
        timeout: FAVORITE_MUTATION_TIMEOUT_MS,
        payload,
      },
      (config) =>
        api.delete(url, {
          data: payload,
          timeout: config.timeout,
        }),
    );
    notifyFavoriteStateChange(siteOrId, false);
    return response;
  },
  updateNote: (siteId, note = "") =>
    api.put(`/sites/${siteId}/favorite`, { note }),
};

export const searchAPI = {
  search: (params = {}) => api.get("/search", { params }),
  suggest: (q) => api.get("/search/suggest", { params: { q } }),
  hotKeywords: () => api.get("/search/hot-keywords"),
};

const CATEGORY_CACHE_TTL_MS = 60_000;
let cachedCategoriesResponse = null;
let cachedCategoriesExpiresAt = 0;
let pendingCategoriesRequest = null;

function getCategoriesWithCache(config = {}) {
  const { force = false, ...requestConfig } = config;
  const now = Date.now();
  if (!force && cachedCategoriesResponse && now < cachedCategoriesExpiresAt) {
    return Promise.resolve(cachedCategoriesResponse);
  }
  if (!force && pendingCategoriesRequest) return pendingCategoriesRequest;

  const requestPromise = api
    .get("/categories", requestConfig)
    .then((response) => {
      cachedCategoriesResponse = response;
      cachedCategoriesExpiresAt = Date.now() + CATEGORY_CACHE_TTL_MS;
      return response;
    })
    .finally(() => {
      if (pendingCategoriesRequest === requestPromise) {
        pendingCategoriesRequest = null;
      }
    });
  pendingCategoriesRequest = requestPromise;
  return requestPromise;
}

export const categoryAPI = {
  getCategories: (config = {}) => getCategoriesWithCache(config),
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
  getCrawlerReviews: (params = {}) =>
    api.get("/admin/crawler/reviews", { params }),
  getCrawlerReview: (reviewUid) =>
    api.get(`/admin/crawler/reviews/${reviewUid}`),
  assignCrawlerReview: (reviewUid, data) =>
    api.post(`/admin/crawler/reviews/${reviewUid}/assign`, data),
  approveCrawlerReview: (reviewUid, data) =>
    api.post(`/admin/crawler/reviews/${reviewUid}/approve`, data),
  rejectCrawlerReview: (reviewUid, data) =>
    api.post(`/admin/crawler/reviews/${reviewUid}/reject`, data),
  previewCrawlerPublish: (reviewUid, data) =>
    api.post(`/admin/crawler/reviews/${reviewUid}/publish-preview`, data),
  publishCrawlerReview: (reviewUid, data) =>
    api.post(`/admin/crawler/reviews/${reviewUid}/publish`, data),
  retryCrawlerPublish: (publishUid, data) =>
    api.post(`/admin/crawler/publishes/${publishUid}/retry`, data),
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
