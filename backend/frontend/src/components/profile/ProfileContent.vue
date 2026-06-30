<template>
  <section class="panel">
    <div class="heading">
      <p>{{ mode === "history" ? "互动足迹" : "内容管理" }}</p>
      <h1>{{ mode === "history" ? "最近访问" : "我的发布" }}</h1>
    </div>

    <div class="list-card">
      <div v-if="items.length === 0" class="empty">
        {{ mode === "history" ? "暂无互动记录" : "暂无发布内容" }}
      </div>
      <button
        v-for="item in items"
        :key="item.id || item.name || item.title"
        type="button"
        class="row"
        @click="$emit('open-item', item)"
      >
        <span>{{
          item.title || item.target_name || item.name || "未命名内容"
        }}</span>
        <small>{{ item.time || item.date || item.status || "刚刚" }}</small>
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  mode: {
    type: String,
    default: "content",
  },
  items: {
    type: Array,
    default: () => [],
  },
});

defineEmits(["open-item"]);
</script>

<style scoped>
.panel {
  display: grid;
  gap: 20px;
}

.heading p,
.heading h1 {
  margin: 0;
}

.heading p {
  color: #1769aa;
  font-weight: 700;
}

.list-card {
  display: grid;
  max-width: 760px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
}

.row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  border: 0;
  border-bottom: 1px solid #eef3f8;
  padding: 16px 18px;
  text-align: left;
  background: #fff;
  cursor: pointer;
}

.row:last-child {
  border-bottom: 0;
}

.empty {
  padding: 28px;
  color: #64748b;
}

small {
  color: #64748b;
}
</style>
