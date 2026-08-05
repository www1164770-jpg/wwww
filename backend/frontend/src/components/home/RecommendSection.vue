<template>
  <section class="recommend-section">
    <div class="recommend-heading">
      <span class="recommend-label">热门推荐</span>
      <h2>正在被更多人使用的工具</h2>
      <p>精选学习、开发、设计与效率工具，帮助你快速找到合适的资源。</p>
    </div>

    <div class="recommend-grid">
      <article
        v-for="site in displayedSites"
        :key="site.url"
        class="website-card"
      >
        <a
          class="website-card-link"
          :href="site.url"
          target="_blank"
          rel="noopener noreferrer"
          :aria-label="`访问 ${site.name}`"
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
import AppTooltip from "../common/AppTooltip.vue";
import FavoriteStarButton from "../site/FavoriteStarButton.vue";
import SiteLogo from "../site/SiteLogo.vue";
import { featuredWebsites } from "../../data/featuredWebsites";
import { getSiteDescription } from "../../utils/api";

const props = defineProps({
  sites: { type: Array, default: () => featuredWebsites },
});

const displayedSites = computed(() =>
  props.sites.length ? props.sites : featuredWebsites,
);

function siteDescription(site) {
  return getSiteDescription(site);
}
</script>

<style scoped>
.recommend-section {
  width: min(100% - 40px, 1220px);
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
  color: #1f2d45;
  font-size: clamp(32px, 3vw, 48px);
  line-height: 1.2;
}

.recommend-heading p {
  margin: 10px 0 0;
  color: #667085;
  font-size: 16px;
  line-height: 1.65;
}

.recommend-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 18px;
  width: 100%;
}

.website-card {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 190px;
  box-sizing: border-box;
  flex-direction: column;
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.46);
  color: inherit;
  box-shadow: 0 10px 30px rgba(31, 45, 75, 0.08);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  transition:
    transform 0.22s ease,
    border-color 0.22s ease,
    box-shadow 0.22s ease;
}

.website-card:hover {
  border-color: rgba(20, 20, 20, 0.9);
  background: rgba(255, 255, 255, 0.58);
  transform: translateY(-4px);
  box-shadow: 0 16px 36px rgba(31, 45, 75, 0.15);
}

.website-card-link {
  display: flex;
  min-width: 0;
  min-height: 190px;
  box-sizing: border-box;
  flex-direction: column;
  padding: 18px;
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
  background: rgba(255, 255, 255, 0.55);
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
  color: #1f2d45;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.website-description {
  display: -webkit-box;
  margin: 14px 0 16px;
  overflow: hidden;
  color: #5f6b7c;
  font-size: 14px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.website-card-footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-top: auto;
}

.website-category {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  padding: 4px 10px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.58);
  color: #536174;
  font-size: 12px;
  font-weight: 600;
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

  .website-card,
  .website-card-link {
    min-height: 170px;
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
