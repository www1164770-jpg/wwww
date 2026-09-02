<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="hero">
        <div>
          <AnimatedPageTitle>我的收藏</AnimatedPageTitle>
          <p>这里保存了你常用和感兴趣的网站资源。</p>
        </div>
        <label class="filter">
          分类
          <select v-model="selectedCategory">
            <option value="">全部分类</option>
            <option
              v-for="category in categories"
              :key="category.id"
              :value="category.id"
            >
              {{ category.name }}
            </option>
          </select>
        </label>
      </section>

      <LoadingState v-if="isInitialLoading" text="正在加载收藏..." />
      <section v-else-if="isBlockingError" class="favorite-error" role="alert">
        <strong>收藏加载失败</strong>
        <p>{{ errorMessage }}</p>
        <button type="button" :disabled="retrying" @click="retryFavorites">
          {{ retrying ? "正在重试..." : "重新加载" }}
        </button>
      </section>
      <div v-else ref="favoritesPanel">
        <p
          v-if="favoriteStore.isRefreshing"
          class="favorite-background-status"
          role="status"
          aria-live="polite"
        >
          正在同步最新收藏...
        </p>
        <p
          v-if="refreshNotice"
          class="favorite-refresh-status"
          role="status"
          aria-live="polite"
        >
          最新收藏暂时无法更新，当前展示上次加载的结果。
          <button type="button" :disabled="retrying" @click="retryFavorites">
            {{ retrying ? "正在重试..." : "重新加载" }}
          </button>
        </p>
        <SiteList
          :sites="filteredFavorites"
          empty-title="收藏夹还是空的"
          empty-description="浏览网站资源时点击收藏按钮，稍后可以在这里快速找到它们。"
          empty-action-text="浏览网站分类"
          empty-action-to="/categories"
          @visit="visit"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { useRouter } from "vue-router";
import AnimatedPageTitle from "../components/common/AnimatedPageTitle.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SiteList from "../components/site/SiteList.vue";
import { useFavoritesStore } from "../stores/favorites";
import { useUserStore } from "../stores/user";
import { visitSite } from "../utils/siteVisit";

const router = useRouter();
const userStore = useUserStore();
const favoriteStore = useFavoritesStore();
const selectedCategory = ref("");
const retrying = ref(false);
const favoritesPanel = ref(null);

const favorites = computed(() => favoriteStore.items);
const categories = computed(() => {
  const categoryMap = new Map();
  favorites.value.forEach((site) => {
    const id = String(
      site.category_id ?? site.categoryName ?? site.category_name ?? "",
    ).trim();
    const name = String(site.categoryName ?? site.category_name ?? "").trim();
    if (id && name && !categoryMap.has(id)) categoryMap.set(id, { id, name });
  });
  return [...categoryMap.values()];
});
const filteredFavorites = computed(() => {
  if (!selectedCategory.value) return favorites.value;
  return favorites.value.filter((site) => {
    const id = String(
      site.category_id ?? site.categoryName ?? site.category_name ?? "",
    );
    return id === selectedCategory.value;
  });
});
const isInitialLoading = computed(
  () => favoriteStore.status === "loading" && favorites.value.length === 0,
);
const isBlockingError = computed(
  () => favoriteStore.status === "error" && favorites.value.length === 0,
);
const refreshNotice = computed(
  () => Boolean(favoriteStore.error) && favoriteStore.hasSnapshot,
);
const errorMessage = computed(
  () => favoriteStore.error?.message || "收藏服务出现异常，请稍后重试",
);

let favoriteCardsObserver;

function observeFavoriteCards() {
  const elements = Array.from(
    favoritesPanel.value?.querySelectorAll(".reveal-on-scroll") || [],
  );
  const reduceMotion = window.matchMedia?.(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  if (reduceMotion || !("IntersectionObserver" in window)) {
    elements.forEach((element) => element.classList.add("is-visible"));
    return;
  }

  if (!favoriteCardsObserver) {
    favoriteCardsObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          entry.target.classList.toggle("is-visible", entry.isIntersecting);
        });
      },
      { threshold: 0.16, rootMargin: "0px 0px -40px 0px" },
    );
  }

  elements.forEach((element, index) => {
    if (element.dataset.revealBound === "1") return;
    element.style.setProperty(
      "--reveal-delay",
      `${Math.min(index * 35, 220)}ms`,
    );
    element.dataset.revealBound = "1";
    favoriteCardsObserver.observe(element);
  });
}

async function initializeFavoritesPage() {
  await userStore.ensureHydrated();
  if (!userStore.isLoggedIn) {
    await router.replace({
      name: "Login",
      query: { redirect: "/favorites" },
    });
    return;
  }

  const userId = userStore.userInfo?.id ?? userStore.userInfo?.user_id;
  const restored = favoriteStore.restoreFavoriteCache(userId);
  void favoriteStore.loadFavorites({
    keepExistingData: true,
    background: restored,
  });
  await nextTick();
  observeFavoriteCards();
}

async function retryFavorites() {
  if (retrying.value) return;
  retrying.value = true;
  try {
    await favoriteStore.loadFavorites({
      force: true,
      keepExistingData: true,
      background: favoriteStore.hasSnapshot,
    });
  } finally {
    retrying.value = false;
    await nextTick();
    observeFavoriteCards();
  }
}

function visit(site) {
  visitSite(site, { source: "favorite" });
}

onMounted(initializeFavoritesPage);

watch(
  filteredFavorites,
  async () => {
    await nextTick();
    observeFavoriteCards();
  },
  { flush: "post" },
);

onBeforeUnmount(() => {
  favoriteCardsObserver?.disconnect();
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #ffffff;
}

main {
  display: grid;
  gap: 26px;
  width: min(1180px, calc(100% - 40px));
  margin: 48px auto 78px;
}

.hero {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  border-radius: 24px;
  background:
    radial-gradient(
      circle at 12% 22%,
      rgba(191, 245, 237, 0.32),
      transparent 30%
    ),
    linear-gradient(135deg, #ffffff 0%, #fff4f1 100%);
  padding: clamp(32px, 5vw, 64px);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.04);
}

h1 {
  margin: 0 0 10px;
  color: var(--color-heading);
  font-size: clamp(34px, 5vw, 54px);
}

.hero p {
  margin: 0;
  color: #718096;
  line-height: 1.7;
}

.filter {
  display: grid;
  gap: 8px;
  width: min(280px, 100%);
  color: var(--color-heading);
  font-weight: 750;
}

select {
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #ffffff;
  padding: 12px;
}

.favorite-error,
.favorite-refresh-status,
.favorite-background-status {
  border: 1px solid rgba(255, 112, 88, 0.25);
  border-radius: 16px;
  background: #fff8f5;
  color: var(--color-text);
}

.favorite-error {
  display: grid;
  justify-items: center;
  gap: 12px;
  padding: 42px 24px;
  text-align: center;
}

.favorite-error strong {
  color: var(--color-heading);
  font-size: 18px;
}

.favorite-error p,
.favorite-refresh-status {
  margin: 0;
  line-height: 1.65;
}

.favorite-background-status {
  margin: 0;
  border-color: rgba(71, 148, 139, 0.22);
  background: #f3fbfa;
  padding: 10px 16px;
  color: #32766e;
  line-height: 1.65;
}

.favorite-error button,
.favorite-refresh-status button {
  border: 0;
  border-radius: 999px;
  background: var(--color-primary);
  color: #ffffff;
  padding: 10px 16px;
  font: inherit;
  font-weight: 750;
  cursor: pointer;
}

.favorite-error button:disabled,
.favorite-refresh-status button:disabled {
  cursor: wait;
  opacity: 0.6;
}

.favorite-refresh-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 16px;
}

.favorite-refresh-status button {
  flex: 0 0 auto;
  padding: 7px 12px;
  font-size: 13px;
}

@media (max-width: 760px) {
  main {
    width: min(100% - 28px, 1180px);
    margin-top: 32px;
  }

  .hero {
    align-items: stretch;
    flex-direction: column;
  }

  .favorite-refresh-status {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
