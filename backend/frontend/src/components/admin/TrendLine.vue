<template><div class="trend-line"><svg viewBox="0 0 300 110" preserveAspectRatio="none" role="img" aria-label="CTR 趋势"><line x1="10" x2="290" y1="100" y2="100"/><polyline :points="points"/></svg><div v-for="row in rows" :key="row.dimension" class="trend-point"><span>{{ String(row.dimension || '').slice(5) || '-' }}</span><b>{{ Number(row.ctr || 0).toFixed(1) }}%</b></div></div></template>
<script setup>
import { computed } from "vue";
const props = defineProps({ rows: { type: Array, default: () => [] } });
const points = computed(() => { const max = Math.max(1, ...props.rows.map((row) => Number(row.ctr || 0))); const count = Math.max(1, props.rows.length - 1); return props.rows.map((row, index) => `${10 + index * 280 / count},${100 - Number(row.ctr || 0) * 82 / max}`).join(" "); });
</script>
