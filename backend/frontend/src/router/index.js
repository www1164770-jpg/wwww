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
    component: () => import('../views/ProfileView.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach((to, from, next) => {
  if (to.meta.requiresAdmin) {
    const userRole = localStorage.getItem('user_role')
    const isLoggedIn = localStorage.getItem('is_logged_in') === 'true'

    if (!isLoggedIn) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }

    if (userRole !== 'admin') {
      alert('无权访问管理后台')
      next('/')
      return
    }
  }

  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('access_token')
    const refreshToken = localStorage.getItem('refresh_token')

    if (!token && !refreshToken) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  next()
})

export default router
