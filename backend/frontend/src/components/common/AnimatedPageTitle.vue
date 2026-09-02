<template>
  <component
    :is="as"
    ref="titleRef"
    class="animated-page-title"
    :class="{
      'animated-page-title--animated': animation,
      'is-visible': isVisible,
    }"
    :style="titleStyle"
  >
    <span class="animated-page-title__measure">
      <slot>{{ text }}</slot>
    </span>
    <span class="animated-page-title__layer animated-page-title__outline" aria-hidden="true">
      <slot>{{ text }}</slot>
    </span>
    <span class="animated-page-title__layer animated-page-title__fill" aria-hidden="true">
      <slot>{{ text }}</slot>
    </span>
  </component>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  as: {
    type: String,
    default: "h1",
  },
  text: {
    type: String,
    default: "",
  },
  animation: {
    type: Boolean,
    default: true,
  },
  color: {
    type: String,
    default: "",
  },
  replayOnEnter: {
    type: Boolean,
    default: false,
  },
  threshold: {
    type: Number,
    default: 0.62,
  },
});

const titleRef = ref(null);
const isVisible = ref(!props.animation);
const titleStyle = computed(() =>
  props.color ? { "--animated-title-color": props.color } : undefined,
);
let observer = null;
let hasPlayed = false;

onMounted(() => {
  if (!props.animation) return;

  const reducedMotion = window.matchMedia?.(
    "(prefers-reduced-motion: reduce)",
  ).matches;
  if (reducedMotion || !("IntersectionObserver" in window)) {
    isVisible.value = true;
    return;
  }

  const enterThreshold = Math.max(0.05, Math.min(1, props.threshold));
  const exitThreshold = Math.min(0.18, enterThreshold / 3);
  observer = new IntersectionObserver(
    ([entry]) => {
      if (!entry) return;
      if (entry.isIntersecting && entry.intersectionRatio >= enterThreshold) {
        if (!isVisible.value) isVisible.value = true;
        hasPlayed = true;
        if (!props.replayOnEnter) {
          observer?.disconnect();
          observer = null;
        }
        return;
      }

      if (
        props.replayOnEnter &&
        hasPlayed &&
        (!entry.isIntersecting || entry.intersectionRatio <= exitThreshold)
      ) {
        isVisible.value = false;
      }
    },
    { threshold: [0, exitThreshold, enterThreshold] },
  );
  observer.observe(titleRef.value);
});

onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
});
</script>

<style scoped>
.animated-page-title {
  --animated-title-color: var(--heading-text-color, var(--app-text-primary));
  --animated-title-outline-duration: 520ms;
  --animated-title-fill-delay: 630ms;
  --animated-title-fill-duration: 650ms;
  --animated-title-easing: cubic-bezier(0.22, 1, 0.36, 1);

  position: relative;
  isolation: isolate;
  color: var(--animated-title-color);
}

.animated-page-title__measure,
.animated-page-title__layer {
  display: block;
  width: 100%;
  font: inherit;
  letter-spacing: inherit;
  line-height: inherit;
  overflow-wrap: inherit;
  text-align: inherit;
  text-transform: inherit;
  white-space: inherit;
}

.animated-page-title__measure {
  color: transparent;
  -webkit-text-fill-color: transparent;
  text-shadow: none;
}

.animated-page-title__layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.animated-page-title__outline {
  color: transparent;
  -webkit-text-fill-color: transparent;
  -webkit-text-stroke: clamp(1px, 0.024em, 1.5px)
    var(--animated-title-color);
}

.animated-page-title__fill {
  color: var(--animated-title-color);
  -webkit-text-fill-color: var(--animated-title-color);
}

.animated-page-title--animated .animated-page-title__outline,
.animated-page-title--animated .animated-page-title__fill {
  clip-path: inset(0 100% 0 0);
  will-change: clip-path;
}

.animated-page-title--animated.is-visible .animated-page-title__outline {
  animation: animated-page-title-outline
    var(--animated-title-outline-duration) var(--animated-title-easing) forwards;
}

.animated-page-title--animated.is-visible .animated-page-title__fill {
  animation: animated-page-title-fill var(--animated-title-fill-duration)
    var(--animated-title-easing) var(--animated-title-fill-delay) forwards;
}

.animated-page-title:not(.animated-page-title--animated)
  .animated-page-title__outline {
  clip-path: inset(0 100% 0 0);
}

.animated-page-title:not(.animated-page-title--animated)
  .animated-page-title__fill {
  clip-path: inset(0 0 0 0);
}

@keyframes animated-page-title-outline {
  from {
    clip-path: inset(0 100% 0 0);
  }

  to {
    clip-path: inset(0 0 0 0);
  }
}

@keyframes animated-page-title-fill {
  from {
    clip-path: inset(0 100% 0 0);
  }

  to {
    clip-path: inset(0 0 0 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .animated-page-title--animated .animated-page-title__outline {
    clip-path: inset(0 100% 0 0);
    animation: none;
  }

  .animated-page-title--animated .animated-page-title__fill {
    clip-path: inset(0 0 0 0);
    animation: none;
    will-change: auto;
  }
}
</style>
