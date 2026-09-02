<template>
  <h1 :id="id" class="hero-stroke-title">
    <span class="hero-stroke-title__measure" aria-hidden="true">
      {{ text }}
    </span>
    <span
      class="hero-stroke-title__layer hero-stroke-title__stroke"
      aria-hidden="true"
    >
      {{ text }}
    </span>
    <span
      class="hero-stroke-title__layer hero-stroke-title__fill"
      aria-hidden="true"
    >
      {{ text }}
    </span>
    <span class="hero-stroke-title__sr-only">{{ text }}</span>
  </h1>
</template>

<script setup>
defineProps({
  id: {
    type: String,
    default: "",
  },
  text: {
    type: String,
    required: true,
  },
});
</script>

<style scoped>
.hero-stroke-title {
  --hero-stroke-title-color: var(--heading-text-color, var(--app-text-primary));
  --hero-stroke-width: 1.2px;
  --hero-stroke-duration: 1.6s;
  --hero-fill-delay: 1.8s;
  --hero-fill-duration: 0.9s;
  --hero-stroke-easing: cubic-bezier(0.22, 1, 0.36, 1);

  position: relative;
  isolation: isolate;
  color: var(--hero-stroke-title-color);
  text-shadow: none;
}

.hero-stroke-title__measure,
.hero-stroke-title__layer {
  display: block;
  width: 100%;
  max-width: inherit;
  font: inherit;
  font-stretch: inherit;
  font-style: inherit;
  letter-spacing: inherit;
  line-height: inherit;
  overflow-wrap: inherit;
  text-align: inherit;
  text-transform: inherit;
  white-space: inherit;
  word-spacing: inherit;
}

.hero-stroke-title__measure {
  visibility: hidden;
}

.hero-stroke-title__layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  text-shadow: none;
  transform: none;
  will-change: clip-path;
}

.hero-stroke-title__stroke {
  color: transparent;
  -webkit-text-fill-color: transparent;
  -webkit-text-stroke: var(--hero-stroke-width) var(--hero-stroke-title-color);
  clip-path: inset(0 100% 0 0);
  animation: hero-stroke-title-draw var(--hero-stroke-duration)
    var(--hero-stroke-easing) forwards;
}

.hero-stroke-title__fill {
  color: var(--hero-stroke-title-color);
  -webkit-text-fill-color: var(--hero-stroke-title-color);
  -webkit-text-stroke: 0 transparent;
  clip-path: inset(0 100% 0 0);
  animation: hero-stroke-title-fill var(--hero-fill-duration)
    var(--hero-stroke-easing) var(--hero-fill-delay) forwards;
}

.hero-stroke-title__sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@keyframes hero-stroke-title-draw {
  from {
    clip-path: inset(0 100% 0 0);
  }

  to {
    clip-path: inset(0 0 0 0);
  }
}

@keyframes hero-stroke-title-fill {
  from {
    clip-path: inset(0 100% 0 0);
  }

  to {
    clip-path: inset(0 0 0 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero-stroke-title__stroke {
    clip-path: inset(0 100% 0 0);
    animation: none;
    will-change: auto;
  }

  .hero-stroke-title__fill {
    clip-path: inset(0 0 0 0);
    animation: none;
    will-change: auto;
  }
}
</style>
