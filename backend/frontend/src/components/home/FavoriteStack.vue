<template>
  <section v-if="displaySites.length" class="favorite-band">
    <div class="favorite-stack">
      <div class="favorite-copy">
        <p>常用工具推荐</p>
        <h2>精选高频使用的网站资源</h2>
        <span>适合日常学习、工作和创作的高质量工具。</span>
      </div>

      <div class="favorite-list">
        <article
          v-for="site in displaySites"
          :key="site.id || site.url || site.name"
          class="compact-tool-card"
        >
          <a
            class="compact-tool-card__link"
            :href="normalizeUrl(site.url)"
            target="_blank"
            rel="noopener noreferrer"
            :aria-label="`访问 ${site.name}`"
            @click.stop.prevent="visitSite(site)"
          >
            <SiteLogo
              class="compact-tool-card__logo"
              :name="site.name"
              :url="site.url"
              :logo="site.logo_url"
              size="md"
              decorative
            />
            <div class="compact-tool-card__content">
              <strong class="compact-tool-card__title">{{ site.name }}</strong>
              <AppTooltip
                v-if="siteDescription(site)"
                :content="siteDescription(site)"
                :disabled="!siteDescription(site)"
                :show-on-overflow="true"
              >
                <small
                  class="compact-tool-card__description"
                  data-tooltip-overflow-target
                >
                  {{ siteDescription(site) }}
                </small>
              </AppTooltip>
            </div>
            <ExternalLink
              class="compact-tool-card__external"
              aria-hidden="true"
            />
          </a>
          <FavoriteStarButton :site="site" size="sm" />
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { ExternalLink } from "lucide-vue-next";
import AppTooltip from "../common/AppTooltip.vue";
import FavoriteStarButton from "../site/FavoriteStarButton.vue";
import SiteLogo from "../site/SiteLogo.vue";
import { getSiteDescription, normalizeUrl } from "../../utils/api";

const props = defineProps({
  sites: { type: Array, default: () => [] },
});

const emit = defineEmits(["visit"]);
const displaySites = computed(() =>
  props.sites
    .filter((site) => site?.name && normalizeUrl(site?.url))
    .slice(0, 6),
);

function siteDescription(site) {
  return getSiteDescription(site);
}

function visitSite(site) {
  emit("visit", { ...site, url: normalizeUrl(site.url) });
}
</script>

<style scoped>
.favorite-band {
  margin-top: 54px;
  padding: 96px 0;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.favorite-stack {
  display: grid;
  grid-template-columns: minmax(240px, 370px) 1fr;
  gap: 42px;
  width: min(1200px, calc(100% - 40px));
  margin: 0 auto;
}

.favorite-copy p {
  margin: 0 0 10px;
  color: var(--color-primary);
  font-weight: 850;
}

.favorite-copy h2 {
  margin: 0 0 14px;
  color: var(--color-heading);
  font-size: clamp(32px, 4vw, 46px);
  line-height: 1.14;
}

.favorite-copy span {
  color: var(--color-text);
  line-height: 1.75;
}

.favorite-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.compact-tool-card {
  position: relative;
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
  transition:
    transform var(--transition),
    box-shadow var(--transition),
    border-color var(--transition);
}

.compact-tool-card:hover {
  border-color: rgba(255, 112, 88, 0.34);
  transform: translateY(-4px);
  box-shadow: var(--shadow-card);
}

.compact-tool-card__link {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 13px;
  padding: 16px 54px 16px 16px;
  color: inherit;
  text-decoration: none;
}

.compact-tool-card__link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}

.compact-tool-card__logo {
  flex: 0 0 auto;
}

.compact-tool-card__content {
  min-width: 0;
}

.compact-tool-card__title,
.compact-tool-card__description {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compact-tool-card__title {
  color: var(--color-heading);
}

.compact-tool-card__description {
  margin-top: 4px;
  color: var(--color-text);
  font-size: 12px;
}

.compact-tool-card__external {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  margin-left: auto;
  color: var(--color-primary);
}

@media (max-width: 820px) {
  .favorite-stack {
    grid-template-columns: 1fr;
    width: min(100% - 28px, 1200px);
  }
}

@media (max-width: 520px) {
  .favorite-list {
    grid-template-columns: 1fr;
  }
}

@media (prefers-reduced-motion: reduce) {
  .compact-tool-card {
    transition: none;
  }

  .compact-tool-card:hover {
    transform: none;
  }
}
</style>
