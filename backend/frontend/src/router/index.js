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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router