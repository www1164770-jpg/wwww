<template>
  <div class="page">
    <AppHeader />
    <main v-if="site" class="detail">
      <section class="hero">
        <img :src="site.logo_url || fallbackLogo" :alt="site.name" />
        <div>
          <p>{{ site.category_name || "AI resource" }}</p>
          <h1>{{ site.name }}</h1>
          <span>{{ site.summary }}</span>
          <div class="actions">
            <button @click="favorite">Favorite</button>
            <button @click="visit">Visit official site</button>
          </div>
        </div>
      </section>
      <section class="facts">
        <div>
          <strong>Free</strong><span>{{ site.is_free ? "Yes" : "No" }}</span>
        </div>
        <div>
          <strong>Login required</strong
          ><span>{{ site.need_login ? "Yes" : "No" }}</span>
        </div>
        <div>
          <strong>Region</strong><span>{{ site.region }}</span>
        </div>
        <div>
          <strong>Recommend index</strong
          ><span>{{ site.recommend_level || site.quality_score }}</span>
        </div>
        <div>
          <strong>Rating</strong><span>{{ site.rating_avg || 0 }}</span>
        </div>
      </section>
      <section class="content">
        <h2>Details</h2>
        <p>{{ site.description || site.summary }}</p>
        <div class="chips">
          <span v-for="tag in site.tags" :key="tag">{{ tag }}</span>
          <span v-for="occupation in site.occupations" :key="occupation">{{
            occupation
          }}</span>
        </div>
      </section>
      <section>
        <h2>Similar sites</h2>
        <SiteList
          :sites="site.similar_sites || []"
          @favorite="favoriteSimilar"
          @visit="visitSimilar"
        />
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import SiteList from "../components/site/SiteList.vue";
import { favoriteAPI, siteAPI } from "../utils/api";

const route = useRoute();
const router = useRouter();
const site = ref(null);
const fallbackLogo = "https://api.dicebear.com/7.x/shapes/svg?seed=site";

async function load() {
  const response = await siteAPI.getSite(route.params.id);
  site.value = response.data?.data;
}
async function favorite() {
  if (!localStorage.getItem("access_token")) return router.push("/login");
  await favoriteAPI.addFavorite(site.value.id);
}
async function visit() {
  await siteAPI.recordClick(site.value.id).catch(() => {});
  window.open(site.value.url, "_blank", "noopener,noreferrer");
}
async function favoriteSimilar(item) {
  if (!localStorage.getItem("access_token")) return router.push("/login");
  await favoriteAPI.addFavorite(item.id);
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
