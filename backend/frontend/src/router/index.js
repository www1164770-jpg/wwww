import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/Home.vue'
import LoginView from '../views/Login.vue'
import { hasAuthSession } from '../utils/api'

const routes = [
  { path: '/', name: 'Home', component: HomeView },
  { path: '/login', name: 'Login', component: LoginView },
  { path: '/register', name: 'Register', component: () => import('../views/Register.vue') },
  { path: '/questionnaire', name: 'Questionnaire', component: () => import('../views/Questionnaire.vue'), meta: { requiresAuth: true } },
  { path: '/categories', name: 'Categories', component: () => import('../views/Categories.vue') },
  { path: '/category/:id', name: 'CategoryDetail', component: () => import('../views/CategoryDetail.vue') },
  { path: '/search', name: 'SearchResults', component: () => import('../views/SearchResults.vue') },
  { path: '/site/:id', name: 'SiteDetail', component: () => import('../views/SiteDetail.vue') },
  { path: '/favorites', name: 'Favorites', component: () => import('../views/Favorites.vue'), meta: { requiresAuth: true } },
  { path: '/publish', name: 'Publish', component: () => import('../views/Editor.vue') },
  { path: '/audit', name: 'Audit', component: () => import('../views/AuditBoard.vue') },
  { path: '/admin', name: 'Admin', component: () => import('../views/Admin.vue'), meta: { requiresAuth: true } },
  { path: '/dmca', name: 'DMCA', component: () => import('../views/DMCA.vue') },
  { path: '/profile', name: 'Profile', component: () => import('../views/Profile.vue'), meta: { requiresAuth: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach((to, from, next) => {
  const isAuthed = hasAuthSession()
  if (isAuthed) localStorage.setItem('is_logged_in', 'true')

  if (to.meta.requiresAuth && !isAuthed) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  next()
})

export default router
