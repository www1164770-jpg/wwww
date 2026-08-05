<template>
  <div class="category-empty-state">
    <div class="category-empty-state__icon" aria-hidden="true">
      <FolderOpen v-if="type === 'category'" />
      <SearchX v-else />
    </div>

    <h2 class="category-empty-state__title">
      {{ type === "category" ? "该分类的资源正在整理中" : "没有找到匹配的网站" }}
    </h2>

    <p class="category-empty-state__description">
      {{
        type === "category"
          ? "我们正在补充更多优质网站，可以先返回首页浏览其他分类。"
          : "尝试减少筛选条件，或清除筛选后重新查看。"
      }}
    </p>

    <div class="category-empty-state__actions">
      <button
        v-if="type === 'filtered' && hasActiveFilters"
        type="button"
        class="btn-primary category-empty-state__action"
        @click="$emit('clear-filters')"
      >
        清除筛选
      </button>

      <RouterLink
        class="btn-cancel category-empty-state__action"
        to="/"
        @click="$emit('back-home')"
      >
        返回首页
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { FolderOpen, SearchX } from "lucide-vue-next";

defineProps({
  type: { type: String, default: "category" },
  hasActiveFilters: { type: Boolean, default: false },
});

defineEmits(["clear-filters", "back-home"]);
</script>

<style scoped>
.category-empty-state {
  display: flex;
  min-height: 420px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 56px 28px;
  border: 1px dashed rgba(100, 116, 139, 0.24);
  border-radius: 20px;
  background: linear-gradient(
    180deg,
    rgba(248, 250, 252, 0.82),
    rgba(255, 255, 255, 0.96)
  );
  text-align: center;
}

.category-empty-state__icon {
  display: flex;
  width: 58px;
  height: 58px;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
  border-radius: 18px;
  background: #f1f5f9;
  color: #64748b;
}

.category-empty-state__icon :deep(svg) {
  width: 26px;
  height: 26px;
}

.category-empty-state__title {
  margin: 0;
  color: #1e293b;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.4;
}

.category-empty-state__description {
  max-width: 460px;
  margin: 10px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.75;
}

.category-empty-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}

.category-empty-state__action {
  display: inline-grid;
  min-height: 42px;
  place-items: center;
  padding: 0 18px;
  text-decoration: none;
}

.category-empty-state__action:focus-visible {
  outline: 3px solid rgba(255, 112, 88, 0.28);
  outline-offset: 3px;
}

@media (max-width: 640px) {
  .category-empty-state {
    min-height: 340px;
    padding: 42px 20px;
  }

  .category-empty-state__actions {
    width: 100%;
    flex-direction: column;
  }

  .category-empty-state__actions > * {
    width: 100%;
  }
}
</style>
