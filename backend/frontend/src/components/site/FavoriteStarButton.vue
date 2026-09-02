<template>
  <button
    type="button"
    class="favorite-star"
    :class="[
      `favorite-star--${size}`,
      { 'is-favorite': isFavorited, 'is-pending': isPending },
    ]"
    :disabled="disabled || !favoriteKey"
    :aria-label="ariaLabel"
    :aria-pressed="isFavorited"
    :title="ariaLabel"
    @pointerdown.stop
    @mousedown.stop
    @click.stop.prevent="handleToggle"
  >
    <Star
      class="favorite-star__icon"
      :fill="isFavorited ? 'currentColor' : 'none'"
      aria-hidden="true"
    />
  </button>
</template>

<script setup>
import { Star } from "lucide-vue-next";
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  normalizeFavoriteError,
  useFavoritesStore,
} from "../../stores/favorites";
import { useUserStore } from "../../stores/user";
import { getAccessToken } from "../../utils/auth";
import { normalizeSite } from "../../utils/normalizeSite";
import { errorToast, successToast } from "../../utils/toast";

const props = defineProps({
  site: { type: Object, required: true },
  favorited: { type: Boolean, default: false },
  favoritePending: { type: Boolean, default: false },
  size: { type: String, default: "md" },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(["changed"]);
const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const favoritesStore = useFavoritesStore();
const normalizedSite = computed(() => normalizeSite(props.site));
const favoriteKey = computed(() =>
  favoritesStore.getFavoriteKey(normalizedSite.value),
);
const isPending = computed(() =>
  favoritesStore.isPending(normalizedSite.value),
);
const isFavorited = computed(() =>
  favoritesStore.isFavorite(normalizedSite.value),
);
const ariaLabel = computed(() => {
  const name = normalizedSite.value.name || "网站";
  if (!favoriteKey.value) return `${name}暂不可收藏`;
  return `${isFavorited.value ? "取消收藏" : "添加收藏"} ${name}`;
});

onMounted(async () => {
  await userStore.ensureHydrated?.();
  if (userStore.isLoggedIn && !favoritesStore.hasSnapshot) {
    void favoritesStore.loadFavorites({
      keepExistingData: true,
      background: true,
    });
  }
});

function handleToggle() {
  if (props.disabled || !favoriteKey.value) return;
  if (!userStore.isLoggedIn && !getAccessToken()) {
    void router.push({
      path: "/login",
      query: { redirect: route.fullPath },
    });
    return;
  }

  const wasFavorited = isFavorited.value;
  try {
    const syncPromise = favoritesStore.toggleFavorite(normalizedSite.value);
    if (!syncPromise) return;
    const nextFavorited = favoritesStore.isFavorite(normalizedSite.value);
    void syncPromise.catch((requestError) => {
      const normalizedError = normalizeFavoriteError(requestError);
      errorToast(
        normalizedError.message || "鏀惰棌鎿嶄綔澶辫触锛岃绋嶅悗閲嶈瘯",
      );
    });
    emit("changed", {
      site: normalizedSite.value,
      favorited: nextFavorited,
    });
    successToast(wasFavorited ? "已取消收藏" : "已收藏");
  } catch (requestError) {
    const normalizedError = normalizeFavoriteError(requestError);
    errorToast(normalizedError.message || "收藏操作失败，请稍后重试");
  }
}
</script>

<style scoped>
.favorite-star {
  position: absolute;
  z-index: 10;
  top: 18px;
  right: 18px;
  display: inline-flex;
  width: 30px;
  height: 30px;
  min-width: 30px;
  min-height: 30px;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border: 0;
  background: transparent;
  color: var(--favorite-muted-color);
  box-shadow: none;
  cursor: pointer;
  pointer-events: auto;
  touch-action: manipulation;
  transition:
    color 160ms ease,
    opacity 160ms ease;
}

.favorite-star--sm {
  width: 28px;
  height: 28px;
  min-width: 28px;
  min-height: 28px;
}

.favorite-star--lg {
  width: 36px;
  height: 36px;
  min-width: 36px;
  min-height: 36px;
}

.favorite-star:hover:not(:disabled) {
  color: var(--app-text-primary);
  background: transparent;
  box-shadow: none;
}

.favorite-star.is-favorite {
  color: var(--favorite-color);
  background: transparent;
  text-shadow: 0 0 8px rgba(255, 123, 92, 0.35);
}

.favorite-star.is-pending {
  cursor: wait;
  opacity: 0.65;
}

.favorite-star:disabled {
  cursor: not-allowed;
}

.favorite-star__icon {
  width: 21px;
  height: 21px;
  stroke-width: 2;
  pointer-events: none;
  transition:
    color 160ms ease,
    transform 160ms ease;
}

.favorite-star:hover:not(:disabled) .favorite-star__icon {
  transform: scale(1.1);
}

.favorite-star:focus-visible {
  outline: 2px solid rgba(242, 118, 93, 0.45);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .favorite-star,
  .favorite-star__icon {
    transition: none;
  }

  .favorite-star:hover:not(:disabled) .favorite-star__icon {
    transform: none;
  }
}
</style>
