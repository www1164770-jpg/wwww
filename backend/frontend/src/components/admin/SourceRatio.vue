<template><article class="source-ratio"><span>{{ label }}</span><strong>{{ value }}</strong><small>{{ target }}</small></article></template>
<script setup>
defineProps({ label: String, value: [String, Number], target: String });
</script>
