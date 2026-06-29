<template>
  <section class="category-strip" aria-label="热门分类">
    <button
      v-for="category in categories"
      :key="category.id"
      type="button"
      :class="{ active: activeCategory === category.id }"
      @click="$emit('select-category', category.id)"
    >
      {{ category.name }}
    </button>
  </section>
</template>

<script setup>
defineProps({
  categories: {
    type: Array,
    default: () => []
  },
  activeCategory: {
    type: [String, Number],
    default: 'all'
  }
})

defineEmits(['select-category'])
</script>

<style scoped>
.category-strip {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 8px min(6vw, 72px) 28px;
}

button {
  flex: 0 0 auto;
  border: 1px solid #d8e2ee;
  border-radius: 999px;
  padding: 10px 16px;
  color: #334155;
  background: #fff;
  cursor: pointer;
}

button.active,
button:hover {
  color: #fff;
  border-color: #1769aa;
  background: #1769aa;
}

@media (max-width: 640px) {
  .category-strip {
    padding-inline: 20px;
  }
}
</style>
