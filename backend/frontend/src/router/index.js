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
    name: 'audit',
    component: () => import('../views/AuditBoard.vue') 
  },
  { 
    path: '/admin', 
    component: () => import('../views/Admin.vue'),
    meta: { requiresAdmin: true } 
  },
  { 
    path: '/dmca', 
    component: () => import('../views/DMCA.vue') 
  }
]

// 1. ✨ 必须先在这里创建出 router 实例！
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 2. ✨ 然后再在这里给它设置拦截守卫！（必须放在 createRouter 之后，export 之前）
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAdmin) {
    const userRole = localStorage.getItem('user_role'); // 登录时存下的角色
    if (userRole === 'admin') next();
    else {
      alert('无权访问管理后台');
      next('/');
    }
  } else {
    next();
  }
})

// 3. 最后导出
export default router