/**
 * 智汇导航 — 统一 Axios 封装层
 * =====================================
 * 所有后端 API 请求的入口，集中管理：
 *   1. BaseURL（无需每次硬编码）
 *   2. Token 自动注入请求头（Bearer 认证）
 *   3. 401 拦截 → 静默刷新 Token（Refresh Token 机制）
 *   4. 统一错误提示与重定向
 *
 * 使用方式：
 *   import { api, authAPI, userAPI, navAPI, adminAPI, securityAPI, contentAPI } from '@/utils/api'
 */

import axios from 'axios'

// ==================== 1. 创建 Axios 实例 ====================
const api = axios.create({
  baseURL: 'http://127.0.0.1:5000/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

// ==================== 2. 标记是否正在刷新 Token（防止并发 401 重复刷新） ====================
let isRefreshing = false
let pendingRequests = [] // 等待刷新的请求队列

export function getStoredUser() {
  const savedUser = localStorage.getItem('user_info')
  if (!savedUser) return null
  try {
    return JSON.parse(savedUser)
  } catch (_) {
    return null
  }
}

export function setAuthSession({ accessToken, refreshToken = '', user = {} }) {
  if (!accessToken) return
  localStorage.setItem('access_token', accessToken)
  if (refreshToken) localStorage.setItem('refresh_token', refreshToken)
  localStorage.setItem('is_logged_in', 'true')
  const previousUser = getStoredUser() || {}
  localStorage.setItem('user_info', JSON.stringify({ ...previousUser, ...user }))
}

export function clearAuthSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_info')
  localStorage.removeItem('is_logged_in')
}

export function hasAuthSession() {
  return Boolean(localStorage.getItem('access_token') || localStorage.getItem('refresh_token'))
}

/**
 * 将等待中的请求全部重试（用新 Token）
 */
function resolvePendingRequests(newToken) {
  pendingRequests.forEach(({ resolve }) => resolve(newToken))
  pendingRequests = []
}

/**
 * 拒绝所有等待中的请求（刷新失败时）
 */
function rejectPendingRequests(error) {
  pendingRequests.forEach(({ reject }) => reject(error))
  pendingRequests = []
}

// ==================== 3. 请求拦截器：自动携带 Access Token ====================
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ==================== 4. 响应拦截器：401 自动刷新 + 统一错误处理 ====================
api.interceptors.response.use(
  // 正常响应直接透传
  (response) => response,

  // 异常响应统一处理
  async (error) => {
    const originalRequest = error.config

    // --- 4a. 401 未认证：尝试静默刷新 Token ---
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token')

      // 没有 refresh_token 就直接跳登录
      if (!refreshToken) {
        clearAuthAndRedirect()
        return Promise.reject(error)
      }

      // 如果正在刷新中，把当前请求加入等待队列
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingRequests.push({
            resolve: (newToken) => {
              originalRequest.headers['Authorization'] = `Bearer ${newToken}`
              resolve(api(originalRequest))
            },
            reject
          })
        })
      }

      // 开始静默刷新
      originalRequest._retry = true
      isRefreshing = true

      try {
        const res = await axios.post(
          'http://127.0.0.1:5000/api/auth/refresh',
          null,
          { headers: { Authorization: `Bearer ${refreshToken}` } }
        )

        const newAccessToken = res.data.access_token
        setAuthSession({ accessToken: newAccessToken })

        // 重试等待队列中的所有请求
        resolvePendingRequests(newAccessToken)

        // 重试当前请求
        originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`
        return api(originalRequest)
      } catch (refreshError) {
        // 刷新失败 → 踢出登录
        rejectPendingRequests(refreshError)
        clearAuthAndRedirect()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // --- 4b. 403 禁止访问 ---
    if (error.response?.status === 403) {
      console.warn('[API] 403 Forbidden:', error.response.data?.msg || '无权访问')
    }

    // --- 4c. 500 服务器内部错误 ---
    if (error.response?.status >= 500) {
      console.error('[API] Server Error:', error.response.data?.msg || '服务器异常')
    }

    return Promise.reject(error)
  }
)

/**
 * 清除登录状态并跳转到登录页
 */
function clearAuthAndRedirect() {
  clearAuthSession()
  // 避免重复跳转
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

// ==================== 5. 按模块分组的 API 函数 ====================

// --- 认证模块 ---
export const authAPI = {
  /** 发送邮箱验证码 */
  sendCode: (email) => api.post('/auth/send-code', { email }),
  /** 用户注册 */
  register: (data) => api.post('/auth/register', data),
  /** 账号密码登录 */
  login: (account, password) => api.post('/auth/login', { account, password }),
  /** 刷新 Access Token */
  refreshToken: () => {
    const refreshToken = localStorage.getItem('refresh_token')
    return axios.post(
      'http://127.0.0.1:5000/api/auth/refresh',
      null,
      { headers: { Authorization: `Bearer ${refreshToken}` } }
    )
  },
  /** 发送密码重置验证码 */
  sendResetCode: (email) => api.post('/auth/send-reset-code', { email }),
  /** 验证重置密码验证码 */
  verifyResetCode: (email, code) => api.post('/auth/verify-reset-code', { email, code }),
  /** 重置密码 */
  resetPassword: (email, code, newPassword) =>
    api.post('/auth/reset-password', { email, code, new_password: newPassword }),
  /** GitHub OAuth 登录跳转地址 */
  githubLoginUrl: 'http://127.0.0.1:5000/api/login/github'
}

// --- 用户模块 ---
export const userAPI = {
  /** 获取个人中心资料 */
  getProfile: () => api.get('/user/profile'),
  /** 获取个人活动记录 */
  getActivity: () => api.get('/user/activity'),
  /** 修改密码 */
  changePassword: (oldPassword, newPassword) =>
    api.post('/user/password', { old_password: oldPassword, new_password: newPassword }),
  /** 获取用户统计数据 */
  getStats: (username) => api.get(`/user/stats?username=${username}`),
  /** 获取登录设备列表 */
  getDevices: () => api.get('/user/devices'),
  /** 获取用户操作历史 */
  getHistory: () => api.get('/user/history'),
  /** 清空历史记录 */
  clearHistory: () => api.post('/user/history/clear'),
  /** 获取用户发布内容列表 */
  getContents: (status = 'pending') => api.get(`/user/contents?status=${status}`),
  /** 删除用户发布内容 */
  deleteContent: (id) => api.post('/user/contents/delete', { id }),
  /** 注销账户 */
  deleteAccount: (password) => api.post('/user/delete-account', { password }),
  /** 同步用户设置到云端 */
  syncSettings: (settings) => api.post('/user/sync', settings),
  /** 获取云端用户设置 */
  getSettings: (username) => api.get(`/user/settings?username=${username}`),
  /** 更新用户个人信息（昵称/性别/生日/简介） */
  updateProfile: (data) => api.post('/user/profile', data),
  getSurveyStatus: () => api.get('/user/survey_status'),
  /** 提交兴趣问卷 */
  submitSurvey: (interests) => api.post('/user/survey', { interests })
}

// --- 安全模块（绑定/验证） ---
export const securityAPI = {
  /** 发送邮箱验证码（已登录用户绑定用） */
  sendEmailCode: (email) =>
    api.post('/security/send-email-code', { email }),
  /** 发送手机验证码 */
  sendSmsCode: (phone) =>
    api.post('/security/send-sms-code', { phone }),
  /** 绑定邮箱 */
  bindEmail: (email, code) =>
    api.post('/security/bind-email', { email, code }),
  /** 绑定手机 */
  bindPhone: (phone, code) =>
    api.post('/security/bind-phone', { phone, code })
}

// --- 导航数据 ---
export const navAPI = {
  /** 获取全站导航数据（分类 + 网站） */
  getNavData: () => api.get('/nav-data'),
  /** 记录网站点击 */
  recordClick: (id) => api.post('/click', { id }),
  /** 获取收藏列表 */
  getFavorites: () => api.get('/favorites'),
  /** 添加收藏 */
  addFavorite: (websiteId) => api.post('/favorites', { website_id: websiteId }),
  /** 取消收藏 */
  removeFavorite: (websiteId) =>
    api.delete(`/favorites/${websiteId}`),
  /** 推荐新网站 */
  suggestSite: (data) => api.post('/suggest-site', data),
  /** 搜索 */
  search: (query, options = {}) =>
    api.get('/search', { params: { q: query, ...options } }),
  getWebsites: (params = {}) => api.get('/websites', { params }),
  getWebsite: (id) => api.get('/websites/' + id),
  getWebsiteComments: (id) => api.get('/websites/' + id + '/comments'),
  postWebsiteComment: (id, content) => api.post('/websites/' + id + '/comments', { content }),
  rateWebsite: (id, rating) => api.post('/websites/' + id + '/rating', { rating }),
  reportWebsite: (id, reason) => api.post('/websites/' + id + '/report', { reason })
}

// --- 管理后台 ---
export const adminAPI = {
  getOverview: () => api.get('/admin/overview'),
  /** 获取待审核网站列表 */
  getPendingSites: () => api.get('/admin/pending_sites'),
  /** 触发 Hacker News 爬取 */
  crawlHN: () => api.post('/admin/crawl_hn'),
  /** 审核网站（通过/拒绝） */
  reviewSite: (id, action, reason = '') =>
    api.post('/admin/review_site', { id, action, reason }),
  /** 获取管理后台统计数据 */
  getDashboard: () => api.get('/admin/dashboard'),
  /** 获取全量统计数据（ECharts 大盘） */
  getStatsOverview: () => api.get('/admin/stats/overview'),
  /** 封禁/解封用户 */
  toggleUserBan: (userId, banned) =>
    api.post('/admin/user/ban', { user_id: userId, banned }),
  /** 获取用户列表 */
  getUsers: (page = 1, perPage = 20) =>
    api.get(`/admin/users?page=${page}&per_page=${perPage}`),
  /** 获取内容审核列表 */
  getContentAuditList: (status = 'pending', page = 1) =>
    api.get(`/admin/content-audit?status=${status}&page=${page}`),
  /** 审核内容（通过/拒绝） */
  reviewContent: (id, action, reason = '') =>
    api.post('/admin/review-content', { id, action, reason }),
  getWebsites: (params = {}) => api.get('/admin/websites', { params }),
  createWebsite: (data) => api.post('/admin/websites', data),
  updateWebsite: (id, data) => api.put('/admin/websites/' + id, data),
  deleteWebsite: (id) => api.delete('/admin/websites/' + id),
  getCategories: () => api.get('/admin/categories'),
  createCategory: (data) => api.post('/admin/categories', data),
  updateCategory: (id, data) => api.put('/admin/categories/' + id, data),
  deleteCategory: (id) => api.delete('/admin/categories/' + id),
  getTags: () => api.get('/admin/tags'),
  createTag: (data) => api.post('/admin/tags', data),
  updateTag: (id, data) => api.put('/admin/tags/' + id, data),
  deleteTag: (id) => api.delete('/admin/tags/' + id),
  getComments: () => api.get('/admin/comments'),
  reviewComment: (id, status) => api.post('/admin/comments/' + id + '/review', { status }),
  deleteComment: (id) => api.delete('/admin/comments/' + id),
  getReports: () => api.get('/admin/reports'),
  updateReportStatus: (id, status) => api.post('/admin/reports/' + id + '/status', { status }),
  getDmcaList: () => api.get('/admin/dmca'),
  updateDmcaStatus: (id, status) => api.post('/admin/dmca/' + id + '/status', { status })
}

// --- 排行榜 & 资讯 ---
export const feedAPI = {
  /** 获取增长率排行榜 */
  getGrowthRanking: () => api.get('/ranking/growth'),
  /** 获取 24 小时热榜 */
  getHotRanking: () => api.get('/ranking/hot'),
  /** 获取 RSS 资讯 */
  getNews: (prof) => api.get(`/news?prof=${encodeURIComponent(prof)}`),
  /** 获取个性化网站推荐 (v2) */
  getRecommendations: () => api.get('/recommendations/websites'),
  /** 获取文章详情 */
  getArticle: (id) => api.get(`/article/${id}`),
  /** 点赞文章 */
  likeArticle: (id) => api.post(`/article/${id}/like`),
  /** 发表评论 */
  postComment: (articleId, content, parentId = null) =>
    api.post(`/article/${articleId}/comment`, { content, parent_id: parentId }),
  /** 获取评论列表 */
  getComments: (articleId, page = 1) =>
    api.get(`/article/${articleId}/comments?page=${page}`)
}

// --- 通知中心 ---
export const notificationAPI = {
  /** 获取未读通知数 */
  getUnreadCount: () => api.get('/notifications/unread-count'),
  /** 获取通知列表 */
  getNotifications: (page = 1) => api.get(`/notifications?page=${page}`),
  /** 标记通知为已读 */
  markRead: (notificationId) =>
    api.post(`/notifications/${notificationId}/read`),
  /** 全部标记已读 */
  markAllRead: () => api.post('/notifications/read-all')
}

// 导出 axios 实例供特殊场景使用
export default api


