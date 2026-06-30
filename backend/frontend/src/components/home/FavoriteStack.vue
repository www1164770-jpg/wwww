<template>
  <section class="favorite-stack">
    <div>
      <p>FAV STACK</p>
      <h2>我常用的效率工具组合</h2>
      <span>收藏、推荐和高频入口会汇总在这里，方便下次直接打开。</span>
    </div>

    <div class="favorite-list">
      <button
        v-for="site in sites"
        :key="site.id"
        type="button"
        @click="$emit('visit', site)"
      >
        <strong>{{ site.name }}</strong>
        <small>{{ site.desc || site.description || site.url }}</small>
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  sites: {
    type: Array,
    default: () => [],
  },
});

defineEmits(["visit"]);
</script>

<style scoped>
.favorite-stack {
  display: grid;
  grid-template-columns: minmax(220px, 320px) 1fr;
  gap: 24px;
  margin: 40px min(6vw, 72px) 72px;
  border-radius: 8px;
  padding: 28px;
  color: #fff;
  background: #18212f;
}

p {
  margin: 0 0 8px;
  color: #7dd3fc;
  font-weight: 800;
}

h2 {
  margin: 0 0 12px;
  font-size: 30px;
}

span {
  color: #cbd5e1;
  line-height: 1.7;
}

.favorite-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

button {
  display: grid;
  gap: 6px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  padding: 14px;
  color: #fff;
  text-align: left;
  background: rgba(255, 255, 255, 0.08);
  cursor: pointer;
}

small {
  color: #cbd5e1;
}

@media (max-width: 760px) {
  .favorite-stack {
    grid-template-columns: 1fr;
    margin-inline: 20px;
  }

  .favorite-list {
    grid-template-columns: 1fr;
  }
}
</style>
