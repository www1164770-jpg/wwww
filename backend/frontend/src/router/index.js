import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/Home.vue' // 我们下一步会把现在的 App.vue 搬到这里
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
      path: '/audit',
      name: 'audit',
      // 注意：这里的路径要对准你刚才建 AuditBoard.vue 的位置
      // 如果你是建在 components 目录下，就改成 '../components/AuditBoard.vue'
      component: () => import('../views/AuditBoard.vue') 
    }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router