<template>
  <div class="page">
    <AppHeader />
    <main class="detail">
      <LoadingState v-if="loading" text="正在加载网站详情..." />
      <EmptyState
        v-else-if="!site"
        title="未找到网站"
        description="该网站不存在或暂时不可用。"
      />
      <template v-else>
        <section class="hero">
          <img :src="site.logo_url || fallbackLogo" :alt="site.name" />
          <div>
            <p>{{ site.category_name || "AI 资源" }}</p>
            <h1>{{ site.name }}</h1>
            <span>{{ site.summary }}</span>
            <div class="actions">
              <button @click="toggleFavorite">
                {{ site.is_favorited ? "取消收藏" : "收藏" }}
              </button>
              <button @click="visit">访问官网</button>
            </div>
          </div>
        </section>
        <section class="facts">
          <div>
            <strong>是否免费</strong
            ><span>{{ site.is_free ? "是" : "否" }}</span>
          </div>
          <div>
            <strong>是否需要登录</strong
            ><span>{{ site.need_login ? "是" : "否" }}</span>
          </div>
          <div>
            <strong>地区</strong><span>{{ site.region }}</span>
          </div>
          <div>
            <strong>推荐指数</strong
            ><span>{{ site.recommend_level || site.quality_score }}</span>
          </div>
          <div>
            <strong>用户评分</strong><span>{{ site.rating_avg || 0 }}</span>
          </div>
        </section>
        <section class="content">
          <h2>详细介绍</h2>
          <p><strong>链接：</strong> {{ site.url }}</p>
          <p>{{ site.description || site.summary }}</p>
          <div class="chips">
            <span v-for="tag in site.tags" :key="tag">{{ tag }}</span>
            <span v-for="occupation in site.occupations" :key="occupation">{{
              occupation
            }}</span>
          </div>
        </section>
        <section>
          <h2>相似网站推荐</h2>
          <SiteList
            :sites="site.similar_sites || []"
            @favorite="favoriteSimilar"
            @visit="visitSimilar"
          />
        </section>
        <section>
          <h2>评论</h2>
          <EmptyState
            title="评论功能即将开放"
            description="后续可在这里展示用户评价和评分。"
          />
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SiteList from "../components/site/SiteList.vue";
import { favoriteAPI, siteAPI } from "../utils/api";

const route = useRoute();
const router = useRouter();
const site = ref(null);
const loading = ref(false);
const fallbackLogo = "https://api.dicebear.com/7.x/shapes/svg?seed=site";

async function load() {
  loading.value = true;
  try {
    const response = await siteAPI.getSite(route.params.id);
    site.value = response.data?.data ?? response.data ?? null;
  } finally {
    loading.value = false;
  }
}
async function toggleFavorite() {
  if (!localStorage.getItem("access_token")) return router.push("/login");
  if (site.value.is_favorited) {
    await favoriteAPI.removeFavorite(site.value.id);
    site.value.is_favorited = false;
  } else {
    await favoriteAPI.addFavorite(site.value.id);
    site.value.is_favorited = true;
  }
}
async function visit() {
  await siteAPI.recordClick(site.value.id).catch(() => {});
  window.open(site.value.url, "_blank", "noopener,noreferrer");
}
async function favoriteSimilar(item) {
  if (!localStorage.getItem("access_token")) return router.push("/login");
  if (item.is_favorited) {
    await favoriteAPI.removeFavorite(item.id);
    item.is_favorited = false;
  } else {
    await favoriteAPI.addFavorite(item.id);
    item.is_favorited = true;
  }
}
async function visitSimilar(item) {
  await siteAPI.recordClick(item.id).catch(() => {});
  window.open(item.url, "_blank", "noopener,noreferrer");
}
onMounted(load);
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f8fafc;
}
.detail {
  display: grid;
  gap: 24px;
  width: min(1080px, calc(100% - 36px));
  margin: 36px auto;
}
.hero,
.facts,
.content,
section {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 22px;
}
.hero {
  display: flex;
  gap: 20px;
}
img {
  width: 86px;
  height: 86px;
  border-radius: 8px;
}
h1,
h2,
p {
  margin-top: 0;
}
.actions,
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}
button {
  border: 0;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  padding: 11px 14px;
  font-weight: 800;
}
.facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 14px;
}
.facts div,
.chips span {
  display: grid;
  gap: 6px;
  border-radius: 8px;
  background: #f3f4f6;
  padding: 12px;
}
.chips span {
  display: inline-block;
}
</style>
