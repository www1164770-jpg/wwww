<template>
  <div class="trend-bars">
    <div v-for="row in rows" :key="row.dimension" class="trend-row"><span>{{ String(row.dimension || '').slice(5) || '-' }}</span><div><i class="impressions" :style="{ width: width(row.impressions) }"></i><i class="clicks" :style="{ width: width(row.clicks) }"></i><i class="favorites" :style="{ width: width(row.favorites) }"></i><i class="repeat" :style="{ width: width(row.repeat_visits) }"></i></div></div>
    <p><b>曝光</b><b>点击</b><b>收藏</b><b>回访</b></p>
  </div>
</template>
<script setup>
const props = defineProps({ rows: { type: Array, default: () => [] } });
function width(value) { const max = Math.max(1, ...props.rows.flatMap((row) => [row.impressions || 0, row.clicks || 0, row.favorites || 0, row.repeat_visits || 0])); return `${Math.max(2, Number(value || 0) * 100 / max)}%`; }
</script>
