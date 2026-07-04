<template>
  <article class="site-card reveal-on-scroll">
    <div class="site-card__inner">
      <div class="card-head">
        <button
          type="button"
          class="site-card__logo-button"
          :aria-label="`访问 ${site.name || '网站'}`"
          @click="openSite"
        >
          <img
            v-if="logoSrc && !logoFailed"
            :src="logoSrc"
            :alt="`${site.name || '网站'} Logo`"
            @error="useFallbackLogo"
          />
          <span v-else class="site-card__text-logo" aria-hidden="true">
            {{ textLogo }}
          </span>
        </button>

        <div>
          <h3>
            <button
              type="button"
              class="site-card__title-button"
              :aria-label="`访问 ${site.name || '网站'}`"
              @click="openSite"
            >
              {{ site.name }}
            </button>
          </h3>
          <p>{{ site.summary || site.description || "网站资源" }}</p>
        </div>
      </div>

      <small class="reason">
        推荐理由：{{ site.reason || "根据你的职业和兴趣推荐" }}
      </small>

      <div class="meta">
        <span>{{ categoryLabel }}</span>
        <span v-for="tag in visibleTags" :key="tag">{{ tag }}</span>
        <span v-if="hiddenTagCount" class="more-tag"
          >+{{ hiddenTagCount }}</span
        >
        <span v-for="occupation in visibleOccupations" :key="occupation">
          {{ occupation }}
        </span>
      </div>

      <div class="actions">
        <button
          v-if="canUseSiteActions"
          type="button"
          class="favorite-action"
          :disabled="favoritePending"
          :aria-label="favoriteLabel"
          @click="$emit('favorite', site)"
        >
          {{ favoritePending ? "处理中..." : favoriteLabel }}
        </button>
        <button type="button" class="visit" @click="openSite">访问网站</button>
        <RouterLink v-if="canUseSiteActions" :to="`/site/${site.id}`">
          查看详情
        </RouterLink>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { getFaviconUrl, getTextLogo, normalizeUrl } from "../../utils/api";

const props = defineProps({
  site: { type: Object, required: true },
  favorited: { type: Boolean, default: false },
  favoritePending: { type: Boolean, default: false },
});
const emit = defineEmits(["favorite", "visit"]);

const logoFailed = ref(false);
const allTags = computed(() => props.site.tags || []);
const categoryLabel = computed(
  () => props.site.category_name || allTags.value[0] || "网站资源",
);
const logoSrc = computed(() => getFaviconUrl(props.site));
const textLogo = computed(() => getTextLogo(props.site));
const visibleTags = computed(() => allTags.value.slice(0, 3));
const hiddenTagCount = computed(() => Math.max(allTags.value.length - 3, 0));
const visibleOccupations = computed(() =>
  (props.site.occupations || []).slice(0, 3),
);
const isFavorited = computed(
  () => Boolean(props.site.is_favorited) || props.favorited,
);
const favoriteLabel = computed(() => (isFavorited.value ? "取消收藏" : "收藏"));
const canUseSiteActions = computed(
  () => props.site.id && !props.site.external_only,
);

watch(
  () => props.site.logo_url,
  () => {
    logoFailed.value = false;
  },
);

function useFallbackLogo() {
  logoFailed.value = true;
}

function openSite() {
  const normalizedUrl = normalizeUrl(props.site?.url);
  emit("visit", { ...props.site, url: normalizedUrl });
}
</script>

<style scoped>
.site-card {
  min-width: 0;
}

.site-card__inner {
  display: grid;
  gap: 18px;
  min-width: 0;
  min-height: 278px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 22px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
  transition:
    transform var(--transition),
    box-shadow var(--transition),
    border-color var(--transition);
}

.site-card:hover .site-card__inner {
  border-color: rgba(255, 112, 88, 0.32);
  transform: translateY(-5px);
  box-shadow: var(--shadow-card);
}

.card-head {
  display: flex;
  gap: 14px;
  min-width: 0;
}

.site-card__logo-button {
  display: inline-grid;
  width: 56px;
  height: 56px;
  min-width: 56px;
  min-height: 56px;
  place-items: center;
  border: 0;
  border-radius: 18px;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.site-card__logo-button:hover,
.site-card__logo-button:focus-visible {
  transform: translateY(-1px);
  outline: none;
}

.site-card__logo-button img,
.site-card__text-logo {
  width: 56px;
  height: 56px;
  border: 1px solid var(--color-border-soft);
  border-radius: 18px;
  background: var(--color-soft);
}

.site-card__logo-button img {
  object-fit: cover;
}

.site-card__text-logo {
  display: grid;
  place-items: center;
  color: var(--color-primary-dark);
  background: #fff7f4;
  font-size: 20px;
  font-weight: 900;
}

h3 {
  margin: 0 0 7px;
}

.site-card__title-button {
  display: inline;
  min-width: 0;
  min-height: 0;
  border: 0;
  background: transparent;
  color: var(--color-heading);
  padding: 0;
  text-align: left;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.3;
  word-break: break-word;
  cursor: pointer;
}

.site-card__title-button:hover,
.site-card__title-button:focus-visible {
  color: #ff7058;
  text-decoration: underline;
  outline: none;
}

p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: var(--color-text);
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.reason {
  display: block;
  border: 1px solid rgba(255, 112, 88, 0.16);
  border-radius: 16px;
  background: var(--color-soft-orange);
  color: var(--color-primary-dark);
  padding: 10px 12px;
  font-weight: 750;
  line-height: 1.45;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 8px;
  min-width: 0;
}

.meta span {
  max-width: 100%;
  border-radius: var(--radius-pill);
  background: var(--color-soft);
  color: var(--color-text);
  padding: 6px 10px;
  overflow-wrap: anywhere;
  font-size: 12px;
  font-weight: 750;
}

.meta .more-tag {
  color: var(--color-primary-dark);
  background: var(--color-soft-orange);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 9px;
  margin-top: auto;
}

.actions button,
.actions a {
  display: inline-grid;
  min-height: 40px;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: #ffffff;
  color: var(--color-heading);
  padding: 0 14px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 800;
  transition:
    transform var(--transition),
    border-color var(--transition),
    color var(--transition),
    background var(--transition),
    box-shadow var(--transition);
}

.actions button:hover,
.actions a:hover,
.actions button:focus-visible,
.actions a:focus-visible {
  border-color: rgba(255, 112, 88, 0.38);
  color: var(--color-primary);
  transform: translateY(-1px);
  outline: none;
}

.actions button:disabled {
  cursor: wait;
  opacity: 0.68;
  transform: none;
}

.favorite-action:hover,
.favorite-action:focus-visible {
  border-color: rgba(255, 112, 88, 0.58);
  background: var(--color-soft-orange);
  box-shadow: 0 10px 22px rgba(255, 112, 88, 0.12);
}

.visit {
  border-color: var(--color-primary) !important;
  background: var(--color-primary) !important;
  color: #ffffff !important;
  box-shadow: 0 10px 22px rgba(255, 112, 88, 0.18);
}

.visit:hover,
.visit:focus-visible {
  background: var(--color-primary-dark) !important;
  color: #ffffff !important;
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.26);
}

@media (max-width: 520px) {
  .site-card__inner {
    padding: 18px;
  }

  .actions {
    align-items: stretch;
    flex-direction: column;
  }

  .actions button,
  .actions a {
    width: 100%;
  }
}
</style>
