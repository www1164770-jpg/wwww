<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="hero">
        <div>
          <h1>我的收藏</h1>
          <p>这里保存了你常用和感兴趣的网站资源。</p>
        </div>
        <label class="filter">
          分类
          <select v-model="selectedCategory">
            <option value="">全部分类</option>
            <option
              v-for="category in categories"
              :key="category.id || category.name"
              :value="String(category.id || category.name)"
            >
              {{ category.name }}
            </option>
          </select>
        </label>
      </section>

      <LoadingState v-if="loading" text="正在加载收藏..." />
      <EmptyState v-else-if="error" title="收藏加载失败" :description="error" />
      <div v-else ref="favoritesPanel">
        <SiteList
          :sites="filteredFavorites"
          :favorite-ids="favorites.map((site) => site.id)"
          :favorite-pending-ids="favoritePendingIds"
          empty-title="暂无收藏"
          empty-description="去首页发现适合你的 AI 工具"
          empty-action-text="去首页看看"
          empty-action-to="/"
          @favorite="remove"
          @visit="visit"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SiteList from "../components/site/SiteList.vue";
import { categoryAPI, favoriteAPI, siteAPI } from "../utils/api";
import { errorToast, successToast } from "../utils/toast";

const favorites = ref([]);
const categories = ref([]);
const selectedCategory = ref("");
const loading = ref(false);
const error = ref("");
const favoritePendingIds = ref([]);
const favoritesPanel = ref(null);
const filteredFavorites = computed(() => {
  if (!selectedCategory.value) return favorites.value;
  return favorites.value.filter((site) => {
    const id = site.category_id ?? site.category?.id ?? site.category_name;
    return String(id) === selectedCategory.value;
  });
});

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

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [favoriteRes, categoryRes] = await Promise.all([
      favoriteAPI.getFavorites(),
      categoryAPI.getCategories().catch(() => ({ data: { data: [] } })),
    ]);
    const payload = favoriteRes.data?.data ?? favoriteRes.data ?? [];
    favorites.value = payload.items || payload || [];
    favorites.value.forEach((site) => {
      site.is_favorited = true;
    });
    categories.value = categoryRes.data?.data || categoryRes.data || [];
  } catch (err) {
    error.value = err.response?.data?.msg || "收藏加载失败，请稍后重试";
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}
async function remove(site) {
  if (favoritePendingIds.value.includes(site.id)) return;
  favoritePendingIds.value = [...favoritePendingIds.value, site.id];
  try {
    await favoriteAPI.removeFavorite(site.id);
    favorites.value = favorites.value.filter((item) => item.id !== site.id);
    successToast("已取消收藏");
  } catch {
    errorToast("操作失败，请稍后重试");
  } finally {
    favoritePendingIds.value = favoritePendingIds.value.filter(
      (id) => id !== site.id,
    );
  }
}
async function visit(site) {
  await siteAPI.recordClick(site.id).catch(() => {});
  window.open(site.url, "_blank", "noopener,noreferrer");
}
onMounted(async () => {
  await load();
  await nextTick();
  observeFavoriteCards();
});

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

@media (max-width: 760px) {
  main {
    width: min(100% - 28px, 1180px);
    margin-top: 32px;
  }

  .hero {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
