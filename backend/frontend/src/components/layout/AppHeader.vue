<template>
  <header class="app-header">
    <div class="header-inner">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">智</span>
        <span>智汇导航</span>
      </RouterLink>

      <nav class="nav-links" aria-label="主导航">
        <RouterLink to="/">首页</RouterLink>
        <RouterLink to="/#categories" @click="scrollToSection('categories')"
          >分类导航</RouterLink
        >
        <RouterLink to="/#tools" @click="scrollToSection('tools')"
          >AI 工具</RouterLink
        >
        <RouterLink to="/#career" @click="scrollToSection('career')"
          >职业推荐</RouterLink
        >
        <RouterLink to="/#tools" @click="scrollToSection('tools')"
          >热门网站</RouterLink
        >
        <RouterLink to="/#latest" @click="scrollToSection('latest')"
          >最新收录</RouterLink
        >
        <button
          type="button"
          class="nav-ai-login-entry"
          :aria-label="
            loggedIn ? '打开 AI 网站推荐助手' : '登录并使用 AI 网站推荐助手'
          "
          @click="handleAiAssistantEntry"
        >
          AI 助手
        </button>
        <RouterLink v-if="loggedIn" to="/favorites">我的收藏</RouterLink>
      </nav>

      <div class="actions">
        <div v-if="loggedIn" ref="userMenuRef" class="user-menu">
          <button
            class="avatar"
            type="button"
            aria-label="打开用户菜单"
            aria-controls="user-dropdown-menu"
            :aria-expanded="menuOpen"
            @click="toggleMenu"
          >
            {{ initials }}
          </button>
          <div
            v-if="menuOpen"
            id="user-dropdown-menu"
            class="dropdown"
            role="menu"
            aria-label="用户菜单"
          >
            <div class="user-summary" role="none">
              <div class="user-identity">
                <strong :title="displayName">{{ displayName }}</strong>
                <span :title="displayEmail">{{ displayEmail }}</span>
              </div>
              <small>{{ roleLabel }}</small>
            </div>
            <div class="menu-items" role="none">
              <RouterLink to="/profile" role="menuitem" @click="closeMenu">
                个人中心
              </RouterLink>
              <RouterLink to="/favorites" role="menuitem" @click="closeMenu">
                我的收藏
              </RouterLink>
              <button type="button" role="menuitem" @click="logout">
                退出登录
              </button>
            </div>
          </div>
        </div>
        <template v-else>
          <RouterLink class="login-link" to="/login">登录</RouterLink>
          <RouterLink class="primary" to="/register">注册</RouterLink>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useAiAssistantStore } from "../../stores/aiAssistant";
import { useUserStore } from "../../stores/user";
import { useRoute, useRouter } from "vue-router";
import { getAccessToken, isValidAuthToken } from "../../utils/auth";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const aiAssistantStore = useAiAssistantStore();
const menuOpen = ref(false);
const userMenuRef = ref(null);
const authTick = ref(0);

const loggedIn = computed(() => {
  authTick.value;
  route.fullPath;
  return userStore.isLoggedIn && isValidAuthToken(getAccessToken());
});
const user = computed(() => {
  authTick.value;
  route.fullPath;
  return userStore.userInfo;
});
const initials = computed(() =>
  (user.value.username || "U").slice(0, 1).toUpperCase(),
);
const displayName = computed(() => user.value.username || "用户");
const displayEmail = computed(() => user.value.email || "暂无邮箱");
const roleLabel = computed(
  () =>
    ({
      admin: "管理员",
      super_admin: "超级管理员",
      user: "普通用户",
    })[user.value.role || userStore.userRole || "user"] || "普通用户",
);

function scrollToSection(id) {
  if (window.location.pathname !== "/") return;
  const target = document.getElementById(id);
  if (!target) return;
  const top = target.getBoundingClientRect().top + window.scrollY - 88;
  window.scrollTo({ top, behavior: "smooth" });
}

function goToAiAssistantLogin() {
  router.push({ path: "/login", query: { redirect: "/" } });
}

function handleAiAssistantEntry() {
  if (loggedIn.value) {
    aiAssistantStore.openAssistant();
    return;
  }

  goToAiAssistantLogin();
}

function refreshAuthState() {
  authTick.value += 1;
}

function toggleMenu() {
  menuOpen.value = !menuOpen.value;
}

function closeMenu() {
  menuOpen.value = false;
}

function handlePointerDown(event) {
  if (
    menuOpen.value &&
    userMenuRef.value &&
    !userMenuRef.value.contains(event.target)
  ) {
    closeMenu();
  }
}

function handleKeydown(event) {
  if (menuOpen.value && event.key === "Escape") {
    closeMenu();
  }
}

function logout() {
  userStore.logout();
  closeMenu();
  refreshAuthState();
  router.replace("/");
}

watch(() => route.fullPath, closeMenu);

onMounted(() => {
  window.addEventListener("storage", refreshAuthState);
  window.addEventListener("focus", refreshAuthState);
  document.addEventListener("pointerdown", handlePointerDown);
  document.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("storage", refreshAuthState);
  window.removeEventListener("focus", refreshAuthState);
  document.removeEventListener("pointerdown", handlePointerDown);
  document.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  border-bottom: 1px solid rgba(229, 231, 235, 0.78);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(18px);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  width: min(1200px, calc(100% - 40px));
  min-width: 0;
  height: 72px;
  margin: 0 auto;
}

.brand {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 10px;
  color: var(--color-heading);
  font-size: 18px;
  font-weight: 850;
  text-decoration: none;
  white-space: nowrap;
}

.brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 14px;
  color: #ffffff;
  background: linear-gradient(135deg, var(--color-primary), #ff9b75);
  box-shadow: 0 12px 24px rgba(255, 112, 88, 0.2);
}

.nav-links,
.actions {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.nav-links {
  flex: 1;
  justify-content: center;
  overflow-x: auto;
  scrollbar-width: none;
}

.nav-links::-webkit-scrollbar {
  display: none;
}

a {
  color: var(--color-text);
  text-decoration: none;
  font-size: 14px;
  font-weight: 700;
  transition:
    color var(--transition),
    background var(--transition),
    transform var(--transition);
}

.nav-links a,
.nav-ai-login-entry {
  min-height: 40px;
  border-radius: var(--radius-pill);
  padding: 10px 15px;
  white-space: nowrap;
}

.nav-ai-login-entry {
  border: 0;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.nav-links a:hover,
.nav-links a:focus-visible,
.nav-links a.router-link-active,
.nav-ai-login-entry:hover,
.nav-ai-login-entry:focus-visible {
  color: var(--color-primary);
  background: var(--color-soft-orange);
  outline: none;
}

.login-link {
  min-height: 40px;
  border: 1px solid rgba(255, 112, 88, 0.28);
  border-radius: var(--radius-pill);
  background: var(--color-soft-orange);
  color: var(--color-primary);
  padding: 10px 16px;
}

.primary,
.avatar {
  display: inline-grid;
  min-height: 40px;
  place-items: center;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 0 18px;
  box-shadow: 0 12px 24px rgba(255, 112, 88, 0.18);
}

.primary:hover,
.primary:focus-visible,
.avatar:hover,
.avatar:focus-visible {
  background: var(--color-primary-dark);
  color: #ffffff;
  transform: translateY(-1px);
  outline: none;
}

.avatar {
  width: 42px;
  height: 42px;
  border: 0;
  padding: 0;
  font-weight: 850;
  cursor: pointer;
}

.user-menu {
  position: relative;
  flex: 0 0 auto;
}

.dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 40;
  display: grid;
  width: 320px;
  max-width: calc(100vw - 32px);
  max-height: min(520px, calc(100vh - 96px));
  overflow-x: hidden;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: #ffffff;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
}

.user-summary {
  display: grid;
  min-width: 0;
  gap: 10px;
  border-bottom: 1px solid var(--color-border-soft);
  padding: 16px;
}

.user-identity {
  display: grid;
  min-width: 0;
  gap: 4px;
}

.user-identity strong,
.user-identity span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-identity strong {
  color: var(--color-heading);
  font-size: 15px;
}

.user-identity span {
  color: var(--color-muted);
  font-size: 13px;
}

.user-summary small {
  justify-self: start;
  border-radius: var(--radius-pill);
  background: var(--color-soft-orange);
  color: var(--color-primary);
  padding: 4px 9px;
  font-size: 12px;
  font-weight: 800;
}

.menu-items {
  display: grid;
}

.dropdown a,
.dropdown button {
  display: block;
  width: 100%;
  border: 0;
  border-radius: 0;
  background: #ffffff;
  color: var(--color-text);
  padding: 12px 14px;
  text-align: left;
  font: inherit;
  font-size: 14px;
  font-weight: 750;
  box-shadow: none;
  cursor: pointer;
}

.dropdown a:hover,
.dropdown a:focus-visible,
.dropdown button:hover,
.dropdown button:focus-visible {
  background: var(--color-soft-orange);
  color: var(--color-primary);
  outline: none;
}

@media (max-width: 900px) {
  .header-inner {
    width: min(100% - 28px, 1200px);
    height: auto;
    min-height: 72px;
    flex-wrap: wrap;
    padding: 12px 0;
  }

  .nav-links {
    order: 3;
    flex-basis: 100%;
    justify-content: flex-start;
    padding-bottom: 2px;
  }
}

@media (max-width: 560px) {
  .header-inner {
    width: min(100% - 24px, 1200px);
    gap: 12px;
  }

  .brand {
    font-size: 16px;
  }

  .actions {
    gap: 8px;
  }

  .login-link,
  .primary {
    min-height: 38px;
    padding-inline: 13px;
  }

  .dropdown {
    width: min(320px, calc(100vw - 24px));
    max-width: calc(100vw - 24px);
  }
}
</style>
