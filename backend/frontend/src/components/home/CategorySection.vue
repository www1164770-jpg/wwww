<template>
  <section class="home-section category-section">
    <aside class="category-copy reveal-on-scroll">
      <p>热门分类</p>
      <h2>按场景浏览 AI 工具</h2>
      <span>
        从学习、创作、开发到效率办公，把常用资源整理成更容易扫描的分类入口。
      </span>
      <div class="category-menu">
        <RouterLink
          v-for="category in categories"
          :key="category.id"
          :to="`/category/${category.id}`"
        >
          {{ category.name }}
        </RouterLink>
      </div>
    </aside>

    <div v-if="categories.length" class="category-grid">
      <article
        v-for="category in categories"
        :key="category.id"
        class="category-card reveal-on-scroll"
        role="link"
        tabindex="0"
        @click="openCategory(category)"
        @keydown.enter.prevent="openCategory(category)"
        @keydown.space.prevent="openCategory(category)"
      >
        <header class="category-card__header">
          <span>{{ category.icon || "AI" }}</span>
          <div>
            <strong>{{ category.name }}</strong>
            <small>{{
              category.description || "查看该分类下的精选网站资源"
            }}</small>
          </div>
        </header>

        <div v-if="loadingCategorySites" class="category-sites-state">
          正在加载资源...
        </div>
        <div v-else-if="categorySites(category).length" class="category-sites">
          <div
            v-for="site in categorySites(category)"
            :key="site.id || site.url || site.name"
            class="category-site"
            @click.stop
          >
            <button
              type="button"
              class="category-site__identity"
              :aria-label="`访问 ${site.name}`"
              @click="visitSite(site)"
            >
              <span class="category-site__logo">
                <img
                  v-if="siteLogoSrc(site) && !logoFailed(site)"
                  :src="siteLogoSrc(site)"
                  :alt="`${site.name} Logo`"
                  @error="useFallbackLogo(site)"
                />
                <span v-else aria-hidden="true">{{ textLogo(site) }}</span>
              </span>
              <span>
                <b>{{ site.name }}</b>
                <small>{{
                  site.summary || site.description || site.url
                }}</small>
              </span>
            </button>
            <RouterLink
              v-if="canShowDetail(site)"
              class="category-site__detail"
              :to="`/site/${site.id}`"
              @click.stop
            >
              查看详情
            </RouterLink>
          </div>
        </div>
        <div v-else class="category-sites-state">
          <strong>暂无资源</strong>
          <small>去后台添加该分类相关网站</small>
        </div>

        <RouterLink
          class="category-more"
          :to="`/category/${category.id}`"
          @click.stop
        >
          查看更多
        </RouterLink>
      </article>
    </div>
    <EmptyState
      v-else
      title="暂无分类"
      description="分类数据加载后会展示在这里。"
    />
  </section>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import EmptyState from "../common/EmptyState.vue";
import { getFaviconUrl, getTextLogo } from "../../utils/api";

const router = useRouter();
const failedLogoKeys = ref({});

const props = defineProps({
  categories: { type: Array, default: () => [] },
  categorySitesMap: { type: Object, default: () => ({}) },
  loadingCategorySites: { type: Boolean, default: false },
});

const emit = defineEmits(["visit-site"]);

function categorySites(category) {
  return props.categorySitesMap?.[category.id] || [];
}

function siteKey(site) {
  return site?.id || site?.url || site?.name || "";
}

function siteLogoSrc(site) {
  return getFaviconUrl(site);
}

function textLogo(site) {
  return getTextLogo(site);
}

function logoFailed(site) {
  return Boolean(failedLogoKeys.value[siteKey(site)]);
}

function canShowDetail(site) {
  return site?.id && !site.external_only;
}

function openCategory(category) {
  if (category?.id) {
    router.push(`/category/${category.id}`);
  }
}

function visitSite(site) {
  emit("visit-site", site);
}

function useFallbackLogo(site) {
  const key = siteKey(site);
  if (key) {
    failedLogoKeys.value = { ...failedLogoKeys.value, [key]: true };
  }
}
</script>

<style scoped>
.category-section {
  display: grid;
  grid-template-columns: minmax(220px, 310px) 1fr;
  gap: 42px;
  padding: 110px 0 52px;
}

.category-copy {
  align-self: start;
}

.category-copy p {
  margin: 0 0 8px;
  color: var(--color-primary);
  font-weight: 850;
}

.category-copy h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(32px, 4vw, 46px);
  line-height: 1.12;
}

.category-copy > span {
  display: block;
  margin-top: 16px;
  color: var(--color-text);
  line-height: 1.75;
}

.category-menu {
  display: grid;
  gap: 10px;
  margin-top: 30px;
}

.category-menu a {
  border-radius: var(--radius-pill);
  padding: 12px 17px;
  color: var(--color-text);
  text-decoration: none;
  font-weight: 750;
}

.category-menu a:hover,
.category-menu a:first-child {
  color: var(--color-primary);
  background: var(--color-soft-orange);
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.category-card {
  display: grid;
  align-content: start;
  gap: 18px;
  min-height: 330px;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background: #ffffff;
  padding: 22px;
  color: var(--color-heading);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.04);
  transition:
    transform var(--transition),
    box-shadow var(--transition),
    border-color var(--transition);
}

.category-card:hover,
.category-card:focus-visible {
  border-color: rgba(255, 112, 88, 0.34);
  transform: translateY(-4px);
  box-shadow: var(--shadow-card);
  outline: none;
}

.category-card__header {
  display: flex;
  gap: 14px;
  min-width: 0;
}

.category-card__header > span {
  display: grid;
  width: 50px;
  height: 50px;
  min-width: 50px;
  place-items: center;
  border-radius: 18px;
  color: var(--color-primary);
  background: var(--color-soft-orange);
  font-weight: 850;
}

.category-card strong {
  display: block;
  color: var(--color-heading);
  font-size: 18px;
}

.category-card small {
  color: var(--color-muted);
  line-height: 1.55;
}

.category-sites {
  display: grid;
  gap: 10px;
}

.category-site {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  border: 1px solid var(--color-border-soft);
  border-radius: 16px;
  background: var(--color-soft);
  padding: 10px;
  transition:
    transform var(--transition),
    background var(--transition),
    border-color var(--transition);
}

.category-site:hover {
  border-color: rgba(255, 112, 88, 0.24);
  background: #fffaf8;
  transform: translateX(3px);
}

.category-site__identity {
  display: flex;
  min-width: 0;
  min-height: 0;
  align-items: center;
  gap: 10px;
  border: 0;
  background: transparent;
  padding: 0;
  text-align: left;
}

.category-site__identity:hover b,
.category-site__identity:focus-visible b {
  color: #ff7058;
  text-decoration: underline;
}

.category-site__identity:focus-visible {
  outline: none;
}

.category-site__logo {
  display: grid;
  width: 40px;
  height: 40px;
  min-width: 40px;
  place-items: center;
  overflow: hidden;
  border: 1px solid var(--color-border-soft);
  border-radius: 12px;
  background: #ffffff;
  color: var(--color-primary-dark);
  font-weight: 900;
}

.category-site__logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.category-site b,
.category-site small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-site b {
  color: var(--color-heading);
  font-size: 14px;
}

.category-site__detail,
.category-more {
  display: inline-grid;
  min-height: 34px;
  place-items: center;
  border-radius: var(--radius-pill);
  color: var(--color-primary-dark);
  background: var(--color-soft-orange);
  padding: 0 12px;
  text-decoration: none;
  font-size: 12px;
  font-weight: 850;
}

.category-more {
  justify-self: start;
  min-height: 40px;
  margin-top: auto;
  font-size: 13px;
}

.category-sites-state {
  display: grid;
  gap: 4px;
  border: 1px dashed rgba(255, 112, 88, 0.34);
  border-radius: 16px;
  background: #fffaf8;
  color: var(--color-text);
  padding: 16px;
  line-height: 1.5;
}

@media (max-width: 980px) {
  .category-section {
    grid-template-columns: 1fr;
  }

  .category-menu {
    display: flex;
    flex-wrap: wrap;
  }
}

@media (max-width: 720px) {
  .category-section {
    padding-top: 72px;
  }

  .category-grid {
    grid-template-columns: 1fr;
  }

  .category-site {
    grid-template-columns: 1fr;
  }

  .category-site__detail {
    justify-self: start;
  }
}
</style>
