import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// Pinia 状态管理（必须在 Vue Router 之前安装，以便路由守卫可以访问 store）
const pinia = createPinia()
app.use(pinia)

// Vue Router
app.use(router)

app.mount('#app')
