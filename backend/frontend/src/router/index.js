import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/Home.vue'
import LoginView from '../views/Login.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomeView
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView
  },
  {
    path: '/publish',
    name: 'Publish',
    component: () => import('../views/Editor.vue')
  },
  {
    path: '/audit',
    name: 'Audit',
    component: () => import('../views/AuditBoard.vue')
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../views/Admin.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/dmca',
    name: 'DMCA',
    component: () => import('../views/DMCA.vue')
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Home.vue'), // 个人页面复用 Home.vue
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

// ==================== 全局路由守卫 ====================
router.beforeEach((to, from, next) => {
  // --- 管理员权限校验 ---
  if (to.meta.requiresAdmin) {
    const userRole = localStorage.getItem('user_role')
    const isLoggedIn = localStorage.getItem('is_logged_in') === 'true'

    if (!isLoggedIn) {
      // 未登录 → 跳登录页
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }

    if (userRole !== 'admin') {
      alert('无权访问管理后台')
      next('/')
      return
    }
  }

  // --- 需要登录的页面 ---
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('access_token')
    const refreshToken = localStorage.getItem('refresh_token')

    if (!token && !refreshToken) {
      // 完全未登录
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  next()
})

// ==================== 全局 JWT 刷新逻辑（页面加载时自动恢复会话） ====================
// 注意：Token 的静默刷新已由 api.js 的响应拦截器处理。
// 此处仅处理页面初次加载时的会话恢复。

export default router
