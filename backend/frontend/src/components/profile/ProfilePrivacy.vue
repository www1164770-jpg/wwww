<template>
  <section class="panel">
    <div class="heading">
      <p>隐私偏好</p>
      <h1>控制个人数据展示</h1>
    </div>
    <div class="list-card">
      <label class="row">
        <span>公开我的收藏</span>
        <input
          :checked="settings.publicFavorites"
          type="checkbox"
          @change="
            $emit('update:setting', 'publicFavorites', $event.target.checked)
          "
        />
      </label>
      <label class="row">
        <span>隐藏互动足迹</span>
        <input
          :checked="settings.hideFootprint"
          type="checkbox"
          @change="
            $emit('update:setting', 'hideFootprint', $event.target.checked)
          "
        />
      </label>
      <label class="row">
        <span>接收个性化推荐</span>
        <input
          :checked="settings.personalized"
          type="checkbox"
          @change="
            $emit('update:setting', 'personalized', $event.target.checked)
          "
        />
      </label>
    </div>
  </section>
</template>

<script setup>
defineProps({
  settings: {
    type: Object,
    required: true,
  },
});

defineEmits(["update:setting"]);
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
  padding: 16px 18px;
  border-bottom: 1px solid #eef3f8;
}

.row:last-child {
  border-bottom: 0;
}
</style>
