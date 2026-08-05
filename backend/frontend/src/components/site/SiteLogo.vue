<template>
  <img
    v-if="imageSrc && !imageFailed"
    class="site-logo site-logo--image"
    :class="`site-logo--${size}`"
    :src="imageSrc"
    :alt="decorative ? '' : `${label} Logo`"
    :width="pixelSize"
    :height="pixelSize"
    loading="lazy"
    decoding="async"
    @error="handleImageError"
  />
  <span
    v-else
    class="site-logo site-logo--fallback"
    :class="`site-logo--${size}`"
    aria-hidden="true"
  >
    {{ initial }}
  </span>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { resolveSiteLogo } from "../../utils/api";

const props = defineProps({
  name: { type: String, default: "" },
  url: { type: String, default: "" },
  logo: { type: String, default: "" },
  size: {
    type: String,
    default: "md",
    validator: (value) => ["sm", "md", "lg"].includes(value),
  },
  decorative: { type: Boolean, default: false },
});

const imageFailed = ref(false);
const label = computed(() => props.name.trim() || "网站");
const imageSrc = computed(
  () => props.logo || resolveSiteLogo({ url: props.url }),
);
const initial = computed(() => Array.from(label.value)[0]?.toUpperCase() || "?");
const pixelSize = computed(() => ({ sm: 28, md: 36, lg: 48 })[props.size]);

watch(imageSrc, () => {
  imageFailed.value = false;
});

function handleImageError() {
  imageFailed.value = true;
}
</script>

<style scoped>
.site-logo {
  display: inline-grid;
  flex: 0 0 auto;
  place-items: center;
  object-fit: contain;
}

.site-logo--sm {
  width: 28px;
  height: 28px;
}

.site-logo--md {
  width: 36px;
  height: 36px;
}

.site-logo--lg {
  width: 48px;
  height: 48px;
}

.site-logo--fallback {
  border-radius: 8px;
  background: var(--color-soft, #f1f5f9);
  color: var(--color-heading, #1e293b);
  font-size: 0.8em;
  font-weight: 800;
  line-height: 1;
}
</style>
