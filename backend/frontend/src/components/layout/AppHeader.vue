<template>
  <header
    class="app-header"
    :class="{ 'app-header--compact': isCompact }"
    :data-compact="isCompact"
  >
    <div class="header-inner">
      <RouterLink class="brand" to="/" aria-label="知航屿首页">
        <img
          class="brand-logo"
          src="/vocanav-logo.png"
          alt=""
          width="331"
          height="269"
        />
        <span class="brand-name">知航屿</span>
      </RouterLink>

      <nav
        class="nav-links"
        aria-label="主导航"
        data-testid="primary-navigation"
      >
        <RouterLink
          class="nav-item nav-home"
          to="/"
          exact-active-class="is-active"
          data-testid="home-navigation-link"
          aria-label="首页"
          title="首页"
        >
          <svg
            class="home-icon"
            viewBox="0 0 24 24"
            aria-hidden="true"
            fill="none"
          >
            <path
              d="m3 10.75 9-7.5 9 7.5v8a2 2 0 0 1-2 2h-4.25v-6h-5.5v6H5a2 2 0 0 1-2-2v-8Z"
              stroke="currentColor"
              stroke-width="1.7"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </RouterLink>
        <RouterLink
          class="nav-item nav-favorites"
          to="/favorites"
          exact-active-class="is-active"
          data-testid="favorites-navigation-link"
          aria-label="收藏夹"
          title="收藏夹"
        >
          <Star
            class="favorite-star-icon"
            :size="22"
            :stroke-width="1.7"
            aria-hidden="true"
          />
          <span
            v-if="favoriteCount > 0"
            class="favorite-count"
            aria-hidden="true"
          >
            {{ favoriteCount > 99 ? "99+" : favoriteCount }}
          </span>
        </RouterLink>
        <button
          type="button"
          class="nav-item nav-ai-login-entry"
          :class="{ 'is-active': aiAssistantStore.isOpen }"
          :aria-label="loggedIn ? '打开知航AI助手' : '登录并使用知航AI助手'"
          :aria-expanded="loggedIn ? aiAssistantStore.isOpen : undefined"
          data-testid="ai-assistant-entry"
          @click="handleAiAssistantEntry"
        >
          知航AI
        </button>
      </nav>

      <div class="actions">
        <div v-if="loggedIn" ref="userMenuRef" class="user-menu">
          <button
            class="user-trigger"
            type="button"
            aria-label="打开用户菜单"
            aria-controls="user-dropdown-menu"
            :aria-expanded="menuOpen"
            @click="toggleMenu"
          >
            <svg
              class="user-icon"
              viewBox="0 0 24 24"
              aria-hidden="true"
              fill="none"
            >
              <path
                d="M12 12a4.25 4.25 0 1 0 0-8.5 4.25 4.25 0 0 0 0 8.5Zm7.25 8.5a7.25 7.25 0 0 0-14.5 0"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
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
        <RouterLink v-else class="login-link" to="/login">登录</RouterLink>
      </div>
    </div>
  </header>
  <div class="app-header-spacer" aria-hidden="true"></div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Star } from "lucide-vue-next";
import { useRoute, useRouter } from "vue-router";
import { useAiAssistantStore } from "../../stores/aiAssistant";
import { useFavoritesStore } from "../../stores/favorites";
import { useUserStore } from "../../stores/user";
import { getAccessToken, isValidAuthToken } from "../../utils/auth";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const aiAssistantStore = useAiAssistantStore();
const favoriteStore = useFavoritesStore();
const isCompact = ref(false);
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
const favoriteCount = computed(() => favoriteStore.favoriteCount);

function goToAiAssistantLogin() {
  router.push({ path: "/login", query: { redirect: "/" } });
}

async function handleAiAssistantEntry() {
  if (loggedIn.value) {
    if (route.path !== "/") {
      await router.push("/");
    }
    aiAssistantStore.openAssistant();
    return;
  }

  goToAiAssistantLogin();
}

function handleScroll() {
  const nextCompact = window.scrollY > 40;
  if (isCompact.value !== nextCompact) {
    isCompact.value = nextCompact;
  }
}

function refreshAuthState() {
  authTick.value += 1;
}

function syncFavoriteState(nextLoggedIn = loggedIn.value) {
  if (nextLoggedIn) {
    void favoriteStore.loadFavorites({
      keepExistingData: true,
      background: true,
    });
  } else {
    favoriteStore.clearFavoriteState();
  }
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
watch(loggedIn, syncFavoriteState, { immediate: true });

onMounted(() => {
  handleScroll();
  window.addEventListener("scroll", handleScroll, { passive: true });
  window.addEventListener("storage", refreshAuthState);
  window.addEventListener("focus", refreshAuthState);
  document.addEventListener("pointerdown", handlePointerDown);
  document.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("scroll", handleScroll);
  window.removeEventListener("storage", refreshAuthState);
  window.removeEventListener("focus", refreshAuthState);
  document.removeEventListener("pointerdown", handlePointerDown);
  document.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 20px;
  left: 50%;
  z-index: 1000;
  width: max-content;
  max-width: calc(100vw - 24px);
  height: 68px;
  padding: 0 28px;
  border: 1px solid var(--app-card-border);
  border-radius: 34px;
  background-color: var(--app-card-bg);
  box-shadow: var(--app-card-shadow);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
  transform: translateX(-50%);
  transition:
    top 220ms ease,
    height 220ms ease,
    padding 220ms ease,
    gap 220ms ease,
    border-radius 220ms ease,
    box-shadow 220ms ease,
    background-color 220ms ease;
}

.app-header--compact {
  top: 8px;
  height: 48px;
  padding: 0 14px;
  border-radius: 24px;
  background-color: var(--app-card-bg);
  box-shadow: var(--app-card-shadow);
}

.app-header-spacer {
  height: 0;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  width: 100%;
  min-width: 0;
  height: 100%;
  transition: gap 220ms ease;
}

.app-header--compact .header-inner {
  gap: 12px;
}

.brand {
  display: inline-flex;
  align-items: center;
  flex: 0 0 auto;
  gap: 9px;
  min-width: 0;
  min-height: 40px;
  color: var(--color-heading);
  text-decoration: none;
  white-space: nowrap;
  transition:
    gap 220ms ease,
    opacity 180ms ease;
}

.brand:hover,
.brand:focus-visible {
  opacity: 0.78;
  outline: none;
}

.brand:focus-visible {
  border-radius: 8px;
  box-shadow: 0 0 0 2px currentColor;
}

.brand-logo {
  display: block;
  width: auto;
  height: 36px;
  flex: 0 0 auto;
  object-fit: contain;
  transition:
    width 220ms ease,
    height 220ms ease;
}

.brand-name {
  overflow: hidden;
  color: var(--app-text-primary);
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1;
  text-overflow: clip;
  transition: font-size 220ms ease;
}

.app-header--compact .brand {
  gap: 7px;
}

.app-header--compact .brand-logo {
  height: 26px;
}

.app-header--compact .brand-name {
  font-size: 15px;
}

.nav-links,
.actions {
  display: flex;
  align-items: center;
  min-width: 0;
}

.nav-links {
  justify-content: center;
  gap: 28px;
  transition: gap 220ms ease;
}

.app-header--compact .nav-links {
  gap: 12px;
}

.nav-item {
  position: relative;
  display: inline-grid;
  width: 40px;
  min-width: 40px;
  height: 40px;
  min-height: 40px;
  place-items: center;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: var(--color-heading);
  padding: 0;
  font-size: 14px;
  font-weight: 800;
  line-height: 1;
  text-decoration: none;
  opacity: 0.72;
  cursor: pointer;
  transition:
    width 220ms ease,
    height 220ms ease,
    color 180ms ease,
    opacity 180ms ease;
}

.nav-item::after {
  position: absolute;
  right: 9px;
  bottom: 3px;
  left: 9px;
  height: 1px;
  border-radius: 1px;
  background: currentColor;
  content: "";
  opacity: 0;
  transform: scaleX(0.45);
  transition:
    opacity 180ms ease,
    transform 180ms ease;
}

.nav-item:hover,
.nav-item:focus-visible,
.nav-item.is-active {
  color: var(--app-text-primary);
  opacity: 1;
  outline: none;
}

.nav-item:focus-visible {
  box-shadow: 0 0 0 2px currentColor;
}

.nav-item.is-active::after {
  opacity: 0.72;
  transform: scaleX(1);
}

.home-icon {
  width: 22px;
  height: 22px;
  transition:
    width 220ms ease,
    height 220ms ease;
}

.app-header--compact .home-icon {
  width: 18px;
  height: 18px;
}

.favorite-star-icon {
  width: 22px;
  height: 22px;
  transition:
    width 220ms ease,
    height 220ms ease;
}

.app-header--compact .favorite-star-icon {
  width: 18px;
  height: 18px;
}

.favorite-count {
  position: absolute;
  top: 0;
  right: 0;
  display: grid;
  min-width: 16px;
  height: 16px;
  place-items: center;
  border: 2px solid #ffffff;
  border-radius: 999px;
  background: #f36f52;
  color: #ffffff;
  padding: 0 3px;
  font-size: 9px;
  font-weight: 800;
  line-height: 1;
}

.actions {
  flex: 0 0 auto;
}

.login-link {
  display: inline-grid;
  min-width: 54px;
  height: 42px;
  min-height: 42px;
  place-items: center;
  border: 1px solid var(--app-border);
  border-radius: 21px;
  background: transparent;
  color: var(--color-heading);
  padding: 0 14px;
  font-size: 14px;
  font-weight: 750;
  line-height: 1;
  text-decoration: none;
  transition:
    width 220ms ease,
    height 220ms ease,
    min-height 220ms ease,
    padding 220ms ease,
    border-radius 220ms ease,
    border-color 180ms ease,
    opacity 180ms ease;
}

.login-link:hover,
.login-link:focus-visible {
  border-color: var(--app-text-primary);
  opacity: 0.76;
  outline: none;
}

.login-link:focus-visible {
  box-shadow: 0 0 0 2px currentColor;
}

.app-header--compact .login-link {
  min-width: 48px;
  height: 40px;
  min-height: 40px;
  border-radius: 20px;
  padding: 0 10px;
  font-size: 13px;
}

.user-menu {
  position: relative;
  flex: 0 0 auto;
}

.user-trigger {
  display: inline-grid;
  width: 42px;
  min-width: 42px;
  height: 42px;
  min-height: 42px;
  place-items: center;
  border: 1px solid var(--app-border);
  border-radius: 50%;
  background: transparent;
  color: var(--color-heading);
  padding: 0;
  cursor: pointer;
  transition:
    width 220ms ease,
    height 220ms ease,
    min-width 220ms ease,
    min-height 220ms ease,
    border-color 180ms ease,
    opacity 180ms ease;
}

.user-trigger:hover,
.user-trigger:focus-visible {
  border-color: var(--app-text-primary);
  opacity: 0.76;
  outline: none;
}

.user-trigger:focus-visible {
  box-shadow: 0 0 0 2px currentColor;
}

.app-header--compact .user-trigger {
  width: 40px;
  min-width: 40px;
  height: 40px;
  min-height: 40px;
}

.user-icon {
  width: 23px;
  height: 23px;
  transition:
    width 220ms ease,
    height 220ms ease;
}

.app-header--compact .user-icon {
  width: 19px;
  height: 19px;
}

.dropdown {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  z-index: 40;
  display: grid;
  width: 320px;
  max-width: calc(100vw - 24px);
  max-height: min(520px, calc(100vh - 96px));
  overflow-x: hidden;
  overflow-y: auto;
  border: 1px solid var(--app-border);
  border-radius: 16px;
  background: var(--app-surface-strong);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
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
  color: var(--app-text-muted);
  font-size: 13px;
}

.user-summary small {
  justify-self: start;
  border: 1px solid var(--app-border);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-text);
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
  min-height: 42px;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--color-text);
  padding: 12px 14px;
  text-align: left;
  text-decoration: none;
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
  background: var(--app-surface);
  color: var(--app-text-primary);
  outline: none;
}

@media (max-width: 560px) {
  .app-header {
    top: 12px;
    max-width: calc(100vw - 24px);
    padding: 0 10px;
  }

  .app-header--compact {
    top: 8px;
    padding: 0 8px;
  }

  .app-header-spacer {
    height: 0;
  }

  .header-inner,
  .app-header--compact .header-inner {
    gap: 6px;
  }

  .brand {
    gap: 5px;
  }

  .brand-logo {
    height: 28px;
  }

  .brand-name {
    font-size: 14px;
  }

  .app-header--compact .brand {
    gap: 4px;
  }

  .app-header--compact .brand-logo {
    height: 24px;
  }

  .app-header--compact .brand-name {
    font-size: 13px;
  }

  .nav-links,
  .app-header--compact .nav-links {
    gap: 4px;
  }

  .login-link {
    min-width: 46px;
    height: 40px;
    min-height: 40px;
    padding: 0 8px;
    font-size: 13px;
  }

  .user-trigger {
    width: 40px;
    min-width: 40px;
    height: 40px;
    min-height: 40px;
  }

  .dropdown {
    right: -4px;
    width: min(320px, calc(100vw - 24px));
  }
}

@media (max-width: 380px) {
  .app-header {
    padding-right: 8px;
    padding-left: 8px;
  }

  .header-inner,
  .app-header--compact .header-inner {
    gap: 4px;
  }

  .brand-logo {
    height: 26px;
  }

  .brand-name {
    font-size: 13px;
  }

  .nav-links,
  .app-header--compact .nav-links {
    gap: 2px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-header,
  .app-header *,
  .app-header *::before,
  .app-header *::after {
    transition-duration: 0.001ms !important;
  }
}
</style>
