<template>
  <div
    class="site-card-reveal"
    :class="{
      'reveal-on-scroll':
        (!isCategoryVariant && !isCareerVariant) || selectable,
    }"
  >
    <article
      class="site-card website-card"
      :class="{
        'website-card--career': isCareerVariant,
        'website-card--category': isCategoryVariant,
        'website-card--category-static': isCategoryVariant && !selectable,
        'website-card--selectable': selectable,
        'website-card--selected': selectable && selected,
      }"
      :role="selectable ? 'button' : undefined"
      :tabindex="selectable ? 0 : undefined"
      :aria-pressed="selectable ? selected : undefined"
      :aria-expanded="selectable ? selected : undefined"
      @click="handleCardClick"
      @keydown.enter.prevent="handleCardClick"
      @keydown.space.prevent="handleCardClick"
    >
      <FavoriteStarButton
        class="site-card__favorite"
        :site="site"
        :favorited="favorited"
        :favorite-pending="favoritePending"
      />

      <template v-if="isCareerVariant">
        <header class="site-card-header">
          <a
            class="site-card-icon"
            :href="normalizedSiteUrl"
            target="_blank"
            rel="noopener noreferrer"
            :aria-label="`打开 ${site.name || '网站'}`"
            @click.stop.prevent="openSite"
          >
            <SiteLogo
              :name="site.name"
              :url="normalizedSiteUrl"
              :logo="site.logo_url || site.logo"
              size="lg"
              decorative
            />
          </a>

          <div class="site-card-identity">
            <a
              class="site-card-name"
              :href="normalizedSiteUrl"
              target="_blank"
              rel="noopener noreferrer"
              @click.stop.prevent="openSite"
            >
              {{ site.name || "未命名网站" }}
            </a>
          </div>
        </header>

        <AppTooltip
          :content="siteDescription"
          :disabled="!siteDescription"
          :show-on-overflow="true"
        >
          <p
            class="site-card-description site-card__description"
            data-testid="career-site-summary"
            data-tooltip-overflow-target
          >
            {{ siteDescription }}
          </p>
        </AppTooltip>
      </template>

      <div v-else class="site-card__inner">
        <div class="card-head">
          <div
            v-if="isCategoryVariant && !selectable"
            class="site-card__logo-button site-card__logo-static"
            aria-hidden="true"
          >
            <SiteLogo
              :name="site.name"
              :url="normalizedSiteUrl"
              :logo="site.logo_url || site.logo"
              size="lg"
              decorative
            />
          </div>
          <button
            v-else
            type="button"
            class="site-card__logo-button"
            :aria-label="`访问 ${site.name || '网站'}`"
            @click.stop="handleSitePrimaryClick"
          >
            <SiteLogo
              :name="site.name"
              :url="normalizedSiteUrl"
              :logo="site.logo_url || site.logo"
              size="lg"
              decorative
            />
          </button>

          <div>
            <h3>
              <span
                v-if="isCategoryVariant && !selectable"
                class="site-card__title"
              >
                {{ site.name }}
              </span>
              <button
                v-else
                type="button"
                class="site-card__title-button"
                :aria-label="`访问 ${site.name || '网站'}`"
                @click.stop="handleSitePrimaryClick"
              >
                {{ site.name }}
              </button>
            </h3>
            <AppTooltip
              v-if="siteDescription"
              :content="siteDescription"
              :disabled="!siteDescription"
              :show-on-overflow="true"
            >
              <p class="site-card__description" data-tooltip-overflow-target>
                {{ siteDescription }}
              </p>
            </AppTooltip>
          </div>
        </div>

        <div v-if="showReason" class="site-card__reason">
          <span class="site-card__reason-label">推荐理由</span>
          <span class="site-card__reason-text">{{ recommendationReason }}</span>
        </div>

        <div v-if="!isCategoryVariant || selectable" class="meta">
          <span>{{ categoryLabel }}</span>
          <span v-for="tag in visibleTags" :key="tag">{{ tag }}</span>
          <span v-if="hiddenTagCount" class="more-tag"
            >+{{ hiddenTagCount }}</span
          >
          <span v-for="occupation in visibleOccupations" :key="occupation">
            {{ occupation }}
          </span>
        </div>

        <div
          v-if="isCategoryVariant && !selectable"
          class="website-card__footer"
        >
          <span class="website-card__category">{{ categoryLabel }}</span>
          <a
            v-if="normalizedSiteUrl"
            class="website-card__external"
            :href="normalizedSiteUrl"
            target="_blank"
            rel="noopener noreferrer"
            :aria-label="`访问 ${site.name || '网站'}`"
            @click.stop
          >
            <ExternalLink aria-hidden="true" />
          </a>
        </div>

        <div v-else-if="!hideActions" class="actions">
          <button type="button" class="visit" @click.stop="openSite">
            访问网站
          </button>
          <RouterLink
            v-if="canUseSiteActions"
            :to="`/site/${site.id}`"
            @click.stop
          >
            查看详情
          </RouterLink>
        </div>
      </div>
    </article>
  </div>
</template>

<script setup>
import { ExternalLink } from "lucide-vue-next";
import { computed } from "vue";
import AppTooltip from "../common/AppTooltip.vue";
import FavoriteStarButton from "./FavoriteStarButton.vue";
import SiteLogo from "./SiteLogo.vue";
import { getSiteDescription, normalizeUrl } from "../../utils/api";

const props = defineProps({
  site: { type: Object, required: true },
  variant: { type: String, default: "default" },
  showReason: { type: Boolean, default: false },
  favorited: { type: Boolean, default: false },
  favoritePending: { type: Boolean, default: false },
  selectable: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
  hideActions: { type: Boolean, default: false },
});
const emit = defineEmits(["visit", "select"]);

const allTags = computed(() =>
  Array.isArray(props.site.tags) ? props.site.tags : [],
);
const categoryLabel = computed(
  () => props.site.category_name || allTags.value[0] || "网站资源",
);
const isCareerVariant = computed(() => props.variant === "career");
const isCategoryVariant = computed(() => props.variant === "category");
const normalizedSiteUrl = computed(() => normalizeUrl(props.site?.url));
const recommendationReason = computed(
  () =>
    props.site.reason ||
    props.site.recommend_reason ||
    props.site.recommendation_reason ||
    props.site.match_reason ||
    props.site.summary ||
    props.site.description ||
    "该网站的功能与你当前选择的职业需求较为匹配。",
);
const siteDescription = computed(() => getSiteDescription(props.site));
const visibleTags = computed(() => allTags.value.slice(0, 3));
const hiddenTagCount = computed(() => Math.max(allTags.value.length - 3, 0));
const visibleOccupations = computed(() =>
  (props.site.occupations || []).slice(0, 3),
);
const canUseSiteActions = computed(
  () => props.site.id && !props.site.external_only,
);

function handleCardClick() {
  if (props.selectable) emit("select", props.site);
  else if (isCareerVariant.value) openSite();
}

function handleSitePrimaryClick() {
  if (props.selectable) {
    handleCardClick();
    return;
  }
  openSite();
}

function openSite() {
  emit("visit", { ...props.site, url: normalizedSiteUrl.value });
}
</script>

<style scoped>
.site-card-reveal {
  min-width: 0;
}

.website-card {
  position: relative;
  display: block;
  height: 100%;
  min-width: 0;
  border: 1px solid #dfe3e8 !important;
  background: #ffffff !important;
  color: inherit;
  text-decoration: none;
  cursor: pointer;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04) !important;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease,
    background-color 180ms ease;
}

.website-card--selectable {
  cursor: pointer;
}

.website-card--category .site-card__inner {
  min-height: 220px;
}

.website-card--category-static {
  cursor: default;
}

.website-card--category .meta {
  margin-top: auto;
}

.website-card--selected,
.website-card--selected:hover,
.website-card--selected:focus-visible {
  border-color: var(--color-primary) !important;
  box-shadow:
    0 14px 30px rgba(15, 23, 42, 0.08),
    0 0 0 2px rgba(255, 112, 88, 0.13) !important;
}

.website-card--career {
  display: flex;
  flex-direction: column;
  min-height: 180px;
  padding: 22px;
  padding-right: 58px;
  overflow: visible;
  border-radius: 18px !important;
  color: #172033;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.035) !important;
  transition: all 0.3s ease;
}

.site-card__inner {
  display: grid;
  gap: 18px;
  min-width: 0;
  min-height: 278px;
  padding: 22px;
}

@media (hover: hover) and (pointer: fine) {
  .website-card:hover {
    border-color: #111111 !important;
    transform: translateY(-2px);
    box-shadow:
      0 14px 30px rgba(15, 23, 42, 0.08),
      0 4px 10px rgba(15, 23, 42, 0.05) !important;
  }

  .website-card--career:hover {
    border-color: rgba(240, 100, 80, 0.48) !important;
    transform: translateY(-4px);
    box-shadow:
      0 18px 34px rgba(15, 23, 42, 0.12),
      0 6px 14px rgba(240, 100, 80, 0.1) !important;
  }
}

.website-card:focus-visible {
  border-color: #111111 !important;
  transform: translateY(-2px);
  box-shadow:
    0 14px 30px rgba(15, 23, 42, 0.08),
    0 4px 10px rgba(15, 23, 42, 0.05) !important;
  outline: 3px solid rgba(17, 17, 17, 0.14);
  outline-offset: 3px;
}

.website-card:focus-within {
  border-color: #111111 !important;
  box-shadow:
    0 14px 30px rgba(15, 23, 42, 0.08),
    0 4px 10px rgba(15, 23, 42, 0.05) !important;
}

.site-card-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
}

.site-card-icon {
  display: grid;
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  place-items: center;
  overflow: hidden;
  border: 1px solid #e7e9ee;
  border-radius: 12px;
  background: #ffffff;
  text-decoration: none;
}

.site-card-icon img,
.site-card-icon .site-card__text-logo {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 0;
  object-fit: cover;
}

.site-card-icon .site-logo {
  width: 100%;
  height: 100%;
  border-radius: 0;
}

.site-card-icon .site-card__text-logo {
  display: grid;
  place-items: center;
  font-size: 17px;
}

.site-card-identity {
  display: grid;
  min-width: 0;
  gap: 4px;
  padding-top: 2px;
}

.site-card-name {
  overflow: hidden;
  text-decoration: none;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-card-name {
  color: #111827;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.35;
}

.site-card-name:hover,
.site-card-name:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.site-card-icon:focus-visible,
.site-card-name:focus-visible {
  border-radius: 5px;
  outline: 3px solid rgba(17, 17, 17, 0.14);
  outline-offset: 2px;
}

.site-card-description {
  display: -webkit-box;
  min-height: 48px;
  margin: 18px 0 16px;
  overflow: hidden;
  color: #596579;
  font-size: 14px;
  line-height: 1.7;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.site-card__description {
  min-width: 0;
}

.site-card__inner .site-card__description {
  margin: 0;
}

.site-card-tag {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 3px 10px;
  border: 1px solid #e4e7ec;
  border-radius: 999px;
  background: #fafafa;
  color: #667085;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
}

.site-card-tag:first-child {
  border-color: #fed7c9;
  background: #fff8f5;
  color: #f06445;
}

@media (prefers-reduced-motion: reduce) {
  .website-card {
    transition: border-color 100ms linear;
  }

  .website-card:hover,
  .website-card:focus-visible {
    transform: none;
  }
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

.site-card__logo-static {
  cursor: default;
}

.site-card__logo-button img,
.site-card__text-logo {
  width: 56px;
  height: 56px;
  border: 1px solid var(--color-border-soft);
  border-radius: 18px;
  background: var(--color-soft);
}

.site-card__logo-button .site-logo {
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

.site-card__title {
  display: inline-block;
  min-width: 0;
  color: var(--color-heading);
  font-size: 18px;
  font-weight: 800;
  line-height: 1.3;
  overflow-wrap: anywhere;
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

.site-card__reason {
  display: grid;
  gap: 4px;
  border: 1px solid rgba(255, 112, 88, 0.16);
  border-radius: 10px;
  background: var(--color-soft-orange);
  padding: 10px 12px;
}

.site-card__reason-label {
  color: var(--color-primary-dark);
  font-size: 12px;
  font-weight: 800;
}

.site-card__reason-text {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
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

.website-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: auto;
}

.website-card__category {
  max-width: calc(100% - 42px);
  overflow: hidden;
  border-radius: var(--radius-pill);
  background: var(--color-soft-orange);
  color: var(--color-primary-dark);
  padding: 6px 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 750;
}

.website-card__external {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: 11px;
  background: #ffffff;
  color: var(--color-muted);
  text-decoration: none;
  transition:
    transform 180ms ease,
    border-color 180ms ease,
    color 180ms ease,
    background-color 180ms ease;
}

.website-card__external :deep(svg) {
  width: 16px;
  height: 16px;
}

.website-card__external:hover,
.website-card__external:focus-visible {
  border-color: rgba(255, 112, 88, 0.42);
  background: var(--color-soft-orange);
  color: var(--color-primary);
  outline: none;
  transform: translateY(-1px);
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

@media (max-width: 640px) {
  .website-card--career {
    min-height: 0;
    padding: 18px;
    padding-right: 54px;
    border-radius: 16px !important;
  }
}
</style>
