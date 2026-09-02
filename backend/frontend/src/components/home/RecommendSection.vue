<template>
  <section class="recommend-section">
    <div class="recommend-heading">
      <span class="recommend-label reveal-child" style="--reveal-delay: 0ms"
        >热门推荐</span
      >
      <AnimatedPageTitle
        class="reveal-child reveal-title"
        style="--reveal-delay: 80ms"
        as="h2"
        :animation="false"
      >
        正在被更多人使用的工具
      </AnimatedPageTitle>
      <p class="reveal-child reveal-description" style="--reveal-delay: 150ms">
        精选学习、开发、设计与效率工具，帮助你快速找到合适的资源。
      </p>
    </div>

    <div class="recommend-grid">
      <article
        v-for="(site, index) in displayedSites"
        :key="site.url"
        class="website-card reveal-child reveal-card"
        :style="revealCardStyle(index)"
      >
        <a
          class="website-card-link"
          :href="site.url"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="`访问 ${site.name}`"
          @click="recordVisit(site, $event)"
          @auxclick.middle="recordVisit(site, $event)"
        >
          <div class="website-card-header">
            <div class="website-icon-wrapper" aria-hidden="true">
              <SiteLogo
                :name="site.name"
                :url="site.url"
                :logo="site.icon || site.logo_url || site.logo"
                size="md"
                decorative
              />
            </div>
            <h3 class="website-name">{{ site.name }}</h3>
          </div>

          <AppTooltip
            v-if="siteDescription(site)"
            :content="siteDescription(site)"
            :disabled="!siteDescription(site)"
            :show-on-overflow="true"
          >
            <p class="website-description" data-tooltip-overflow-target>
              {{ siteDescription(site) }}
            </p>
          </AppTooltip>

          <div class="website-card-footer">
            <span class="website-category">{{ site.category }}</span>
            <ExternalLink class="website-card__external" aria-hidden="true" />
          </div>
        </a>

        <FavoriteStarButton :site="site" />
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { ExternalLink } from "lucide-vue-next";
import AnimatedPageTitle from "../common/AnimatedPageTitle.vue";
import AppTooltip from "../common/AppTooltip.vue";
import FavoriteStarButton from "../site/FavoriteStarButton.vue";
import SiteLogo from "../site/SiteLogo.vue";
import { featuredWebsites } from "../../data/featuredWebsites";
import { getSiteDescription } from "../../utils/api";
import { cleanSiteDescription } from "../../utils/siteText";
import { visitSite } from "../../utils/siteVisit";

const props = defineProps({
  sites: { type: Array, default: () => featuredWebsites },
});

const displayedSites = computed(() =>
  props.sites.length ? props.sites : featuredWebsites,
);

function revealCardStyle(index) {
  return {
    "--reveal-delay": `${230 + Math.min(index * 35, 350)}ms`,
  };
}

function siteDescription(site) {
  return cleanSiteDescription(
    site?.name || site?.title,
    getSiteDescription(site),
  );
}

function recordVisit(site, event) {
  visitSite(site, { source: "home_recommend", event });
}
</script>

<style scoped>
.recommend-section {
  width: min(var(--container), calc(100% - 40px));
  margin: 0 auto;
  padding: 48px 0 72px;
}

.recommend-heading {
  margin-bottom: 28px;
}

.recommend-label {
  display: inline-block;
  margin-bottom: 8px;
  color: #ff6b4a;
  font-size: 14px;
  font-weight: 700;
}

.recommend-heading h2 {
  margin: 0;
  color: var(--app-text-primary);
  font-size: clamp(32px, 3vw, 48px);
  line-height: 1.2;
}

.recommend-heading p {
  margin: 10px 0 0;
  color: var(--app-text-secondary);
  font-size: 16px;
  line-height: 1.65;
}

.recommend-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 20px;
  width: 100%;
}

.website-card {
  position: relative;
  display: flex;
  height: 160px;
  min-width: 0;
  min-height: 160px;
  max-height: 160px;
  box-sizing: border-box;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--app-border);
  border-radius: var(--radius-card);
  background: var(--app-card-bg);
  backdrop-filter: blur(var(--app-blur));
  color: inherit;
  box-shadow: var(--app-card-shadow);
  transition:
    transform 0.22s ease,
    border-color 0.22s ease,
    box-shadow 0.22s ease;
}

.website-card:hover {
  border-color: rgba(20, 20, 20, 0.9);
  background: var(--app-card-hover-bg);
  transform: translateY(-4px);
  box-shadow: var(--app-card-hover-shadow);
}

.website-card-link {
  display: flex;
  height: 100%;
  min-width: 0;
  min-height: 0;
  box-sizing: border-box;
  flex-direction: column;
  padding: 12px 18px;
  color: inherit;
  text-decoration: none;
}

.website-card-link:focus-visible {
  outline: 2px solid #1a1a1a;
  outline-offset: 3px;
}

.website-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.website-icon-wrapper {
  display: flex;
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 12px;
  background: var(--app-container-bg);
}

.website-icon-wrapper .site-logo {
  width: 44px;
  height: 44px;
  border-radius: 12px;
}

.website-name {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: var(--app-text-primary);
  font-size: 17px;
  font-weight: 700;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.website-description {
  display: -webkit-box;
  margin: 10px 0 8px;
  overflow: hidden;
  color: var(--app-text-secondary);
  font-size: 14px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.website-card-footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: auto;
}

.website-category {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  max-width: 100%;
  overflow: hidden;
  border-radius: var(--radius-pill);
  background: var(--color-soft-orange);
  color: var(--color-primary-dark);
  padding: 4px 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  font-weight: 750;
  line-height: 1;
}

.website-card__external {
  width: 16px;
  height: 16px;
  color: #98a2b3;
  opacity: 0;
  transform: translate(-2px, 2px);
  transition:
    opacity 180ms ease,
    color 180ms ease,
    transform 180ms ease;
}

.website-card:hover .website-card__external,
.website-card-link:focus-visible .website-card__external {
  color: var(--color-primary);
  opacity: 1;
  transform: translate(0, 0);
}

@media (max-width: 1199px) {
  .recommend-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 899px) {
  .recommend-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 639px) {
  .recommend-section {
    width: min(100% - 28px, 1220px);
  }

  .recommend-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .website-card {
    height: 160px;
    min-height: 160px;
    max-height: 160px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .website-card {
    transition: none;
  }

  .website-card:hover {
    transform: none;
  }

  .website-card__external {
    opacity: 1;
    transform: none;
  }
}
</style>
