import { createApp } from "vue";
import { createPinia } from "pinia";
import "./style.css";
import App from "./App.vue";
import router from "./router";
import revealSection from "./directives/reveal";
import { useUserStore } from "./stores/user";
import { usePersonalizationStore } from "./stores/personalization";

const app = createApp(App);

// Pinia 状态管理（必须在 Vue Router 之前安装，以便路由守卫可以访问 store）
const pinia = createPinia();
app.use(pinia);
useUserStore(pinia).initFromStorage();
usePersonalizationStore(pinia).initFromStorage();

// Vue Router
app.use(router);
app.directive("reveal-section", revealSection);

app.mount("#app");
