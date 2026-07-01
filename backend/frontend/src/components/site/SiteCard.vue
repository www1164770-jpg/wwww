<template>
  <article class="site-card">
    <div class="card-head">
      <img :src="site.logo_url || fallbackLogo" :alt="site.name" />
      <div>
        <h3>{{ site.name }}</h3>
        <p>{{ site.summary || site.description || "实用 AI 资源" }}</p>
      </div>
    </div>

    <small class="reason">
      推荐理由：{{ site.reason || "根据你的职业和兴趣推荐" }}
    </small>

    <div class="meta">
      <span v-for="tag in visibleTags" :key="tag">{{ tag }}</span>
      <span v-for="occupation in visibleOccupations" :key="occupation">
        {{ occupation }}
      </span>
    </div>

    <div class="actions">
      <button type="button" @click="$emit('favorite', site)">
        {{ favorited ? "取消收藏" : "收藏" }}
      </button>
      <button type="button" class="visit" @click="$emit('visit', site)">
        访问网站
      </button>
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
  gap: 18px;
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

.site-card:hover {
  border-color: rgba(255, 112, 88, 0.32);
  transform: translateY(-5px);
  box-shadow: var(--shadow-card);
}

.card-head {
  display: flex;
  gap: 14px;
  min-width: 0;
}

img {
  flex: 0 0 auto;
  width: 56px;
  height: 56px;
  border: 1px solid var(--color-border-soft);
  border-radius: 18px;
  object-fit: cover;
  background: var(--color-soft);
}

h3 {
  margin: 0 0 7px;
  color: var(--color-heading);
  font-size: 18px;
  line-height: 1.3;
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
}

.meta span {
  border-radius: var(--radius-pill);
  background: var(--color-soft);
  color: var(--color-text);
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 750;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 9px;
  margin-top: auto;
}

button,
a {
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
    background var(--transition);
}

button:hover,
a:hover {
  border-color: rgba(255, 112, 88, 0.38);
  color: var(--color-primary);
  transform: translateY(-1px);
}

.visit {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(255, 112, 88, 0.18);
}

.visit:hover {
  background: var(--color-primary-dark);
  color: #ffffff;
}
</style>
