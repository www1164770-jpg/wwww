import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// 关键：必须在 mount 之前 use router
app.use(router)

app.mount('#app')