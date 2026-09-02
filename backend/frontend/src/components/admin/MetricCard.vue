<template><article class="metric-card" :class="{ accent }"><span>{{ label }}</span><strong>{{ value }}</strong></article></template>
<script setup>
defineProps({ label: String, value: [String, Number], accent: Boolean });
</script>
