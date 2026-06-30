<template>
  <article class="site-card">
    <div class="head">
      <img :src="site.logo_url || fallbackLogo" :alt="site.name" />
      <div>
        <h3>{{ site.name }}</h3>
        <p>{{ site.summary || site.description || "实用 AI 资源" }}</p>
        <small class="reason">{{
          site.reason || "根据你的职业和兴趣推荐"
        }}</small>
      </div>
    </div>
    <div class="meta">
      <span v-for="tag in visibleTags" :key="tag">{{ tag }}</span>
      <span v-for="occupation in visibleOccupations" :key="occupation">{{
        occupation
      }}</span>
    </div>
    <div class="actions">
      <button type="button" @click="$emit('favorite', site)">
        {{ favorited ? "取消收藏" : "收藏" }}
      </button>
      <button type="button" @click="$emit('visit', site)">访问网站</button>
      <RouterLink :to="`/site/${site.id}`">查看详情</RouterLink>
    </div>
  </article>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  site: { type: Object, required: true },
  favorited: { type: Boolean, default: false },
});
defineEmits(["favorite", "visit"]);

const fallbackLogo = "https://api.dicebear.com/7.x/shapes/svg?seed=ai-nav";
const visibleTags = computed(() => (props.site.tags || []).slice(0, 4));
const visibleOccupations = computed(() =>
  (props.site.occupations || []).slice(0, 3),
);
</script>

<style scoped>
.site-card {
  display: grid;
  gap: 16px;
  min-height: 230px;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.head {
  display: flex;
  gap: 14px;
}
img {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  object-fit: cover;
  background: #f3f4f6;
}
h3 {
  margin: 0 0 6px;
  color: #111827;
}
p {
  margin: 0;
  color: #6b7280;
  line-height: 1.5;
}
.reason {
  display: block;
  margin-top: 6px;
  color: #2563eb;
  font-weight: 750;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 8px;
}
.meta span {
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
  padding: 5px 9px;
  font-size: 12px;
  font-weight: 700;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: auto;
}
button,
a {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  color: #111827;
  padding: 9px 11px;
  text-decoration: none;
  font-weight: 750;
}
button:last-of-type {
  background: #111827;
  color: #fff;
}
</style>
