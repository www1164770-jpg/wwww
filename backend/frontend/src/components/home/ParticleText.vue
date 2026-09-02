<template>
  <h1
    ref="hostRef"
    :id="id"
    class="particle-text"
    :class="{ 'particle-text--ready': ready }"
  >
    <span class="particle-text__fallback" aria-hidden="true">{{ text }}</span>
    <canvas
      ref="canvasRef"
      class="particle-text__canvas"
      aria-hidden="true"
    ></canvas>
    <span class="particle-text__sr-only">{{ text }}</span>
  </h1>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  id: {
    type: String,
    default: "",
  },
  text: {
    type: String,
    required: true,
  },
});

const hostRef = ref(null);
const canvasRef = ref(null);
const ready = ref(false);

const particles = [];
const pointer = { active: false, x: 0, y: 0 };
const reducedMotionQuery = window.matchMedia(
  "(prefers-reduced-motion: reduce)",
);

let animationFrame = 0;
let resizeTimer = 0;
let resizeObserver = null;
let themeObserver = null;
let canvasContext = null;
let renderColor = "";
let interactionRadius = 90;
let destroyed = false;
let frameNumber = 0;

const SPRING = 0.065;
const FRICTION = 0.86;
const REPEL_STRENGTH = 1.7;
const SWIRL_STRENGTH = 0.22;

function randomBetween(min, max) {
  return min + Math.random() * (max - min);
}

function resolveParticleColor(style) {
  const configuredColor = style
    .getPropertyValue("--particle-title-color")
    .trim();
  if (configuredColor && !configuredColor.startsWith("var(")) {
    return configuredColor;
  }
  return style.color || "#111827";
}

function getFontMetrics(style, availableWidth) {
  const declaredSize = Number.parseFloat(style.fontSize) || 64;
  const weight = style.fontWeight || "800";
  const family = style.fontFamily || "sans-serif";
  const fontStyle = style.fontStyle || "normal";
  const letterSpacing = Number.parseFloat(style.letterSpacing) || 0;
  const measureCanvas = document.createElement("canvas");
  const measureContext = measureCanvas.getContext("2d");
  if (!measureContext) return null;

  measureContext.font = `${fontStyle} ${weight} ${declaredSize}px ${family}`;
  const rawWidth =
    measureContext.measureText(props.text).width +
    Math.max(0, props.text.length - 1) * letterSpacing;
  const fontSize =
    rawWidth > availableWidth
      ? Math.max(18, declaredSize * (availableWidth / rawWidth))
      : declaredSize;

  return {
    family,
    fontSize,
    fontStyle,
    letterSpacing: letterSpacing * (fontSize / declaredSize),
    weight,
  };
}

function createTextMask(width, height, metrics) {
  const mask = document.createElement("canvas");
  mask.width = Math.max(1, Math.round(width));
  mask.height = Math.max(1, Math.round(height));
  const context = mask.getContext("2d", { willReadFrequently: true });
  if (!context) return null;
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#000";
  context.font = `${metrics.fontStyle} ${metrics.weight} ${metrics.fontSize}px ${metrics.family}`;
  context.textAlign = "center";
  context.textBaseline = "middle";

  if (Math.abs(metrics.letterSpacing) < 0.01) {
    context.fillText(props.text, width / 2, height / 2);
  } else {
    const widths = [...props.text].map(
      (character) => context.measureText(character).width,
    );
    const textWidth =
      widths.reduce((sum, value) => sum + value, 0) +
      metrics.letterSpacing * Math.max(0, widths.length - 1);
    let cursor = (width - textWidth) / 2;
    context.textAlign = "left";
    for (let index = 0; index < widths.length; index += 1) {
      context.fillText(props.text[index], cursor, height / 2);
      cursor += widths[index] + metrics.letterSpacing;
    }
  }

  return context.getImageData(0, 0, mask.width, mask.height);
}

function rebuildParticles() {
  const host = hostRef.value;
  const canvas = canvasRef.value;
  if (!host || !canvas || destroyed) return;

  const width = Math.round(host.clientWidth);
  const height = Math.round(host.clientHeight);
  if (width < 1 || height < 1) return;

  const style = getComputedStyle(host);
  const metrics = getFontMetrics(style, width - 8);
  if (!metrics) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const mask = createTextMask(width, height, metrics);
  if (!mask) return;
  const isCompact = width <= 768;
  let gap = isCompact
    ? Math.max(2.4, metrics.fontSize / 15)
    : Math.max(2.7, metrics.fontSize / 30);

  const points = [];
  const collectPoints = () => {
    points.length = 0;
    for (let y = gap / 2; y < height; y += gap) {
      for (let x = gap / 2; x < width; x += gap) {
        const pixelX = Math.min(mask.width - 1, Math.round(x));
        const pixelY = Math.min(mask.height - 1, Math.round(y));
        const alpha = mask.data[(pixelY * mask.width + pixelX) * 4 + 3];
        if (alpha > 92) points.push({ x, y, alpha });
      }
    }
  };

  collectPoints();
  while (points.length > 14000) {
    gap *= 1.08;
    collectPoints();
  }

  particles.length = 0;
  const reducedMotion = reducedMotionQuery.matches;
  for (const point of points) {
    const angle = Math.random() * Math.PI * 2;
    const distance = reducedMotion
      ? 0
      : randomBetween(30, Math.min(118, metrics.fontSize * 1.35));
    particles.push({
      x: point.x + Math.cos(angle) * distance,
      y: point.y + Math.sin(angle) * distance * 0.72,
      vx: reducedMotion ? 0 : randomBetween(-0.55, 0.55),
      vy: reducedMotion ? 0 : randomBetween(-0.45, 0.45),
      targetX: point.x,
      targetY: point.y,
      opacity: 1,
      size: randomBetween(isCompact ? 1 : 1.1, isCompact ? 1.7 : 2.05),
    });
  }

  interactionRadius = Math.min(110, Math.max(72, metrics.fontSize * 1.15));
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  canvas.dataset.particleCount = String(particles.length);
  canvas.dataset.interactionRadius = String(Math.round(interactionRadius));
  canvasContext = canvas.getContext("2d");
  if (!canvasContext) return;
  canvasContext.setTransform(dpr, 0, 0, dpr, 0, 0);
  renderColor = resolveParticleColor(style);
  canvas.dataset.renderColor = renderColor;
  ready.value = particles.length > 0;
  drawFrame();
}

function drawFrame() {
  if (!canvasContext || !canvasRef.value) return;
  const width = canvasRef.value.clientWidth;
  const height = canvasRef.value.clientHeight;
  canvasContext.clearRect(0, 0, width, height);
  canvasContext.globalCompositeOperation = "source-over";
  canvasContext.fillStyle = renderColor;

  for (const particle of particles) {
    canvasContext.globalAlpha = particle.opacity;
    canvasContext.fillRect(
      particle.x - particle.size / 2,
      particle.y - particle.size / 2,
      particle.size,
      particle.size,
    );
  }
  canvasContext.globalAlpha = 1;
}

function animate() {
  if (destroyed) return;
  const reducedMotion = reducedMotionQuery.matches;

  for (const particle of particles) {
    if (reducedMotion) {
      particle.x = particle.targetX;
      particle.y = particle.targetY;
      particle.vx = 0;
      particle.vy = 0;
      continue;
    }

    particle.vx += (particle.targetX - particle.x) * SPRING;
    particle.vy += (particle.targetY - particle.y) * SPRING;

    if (pointer.active) {
      const dx = particle.x - pointer.x;
      const dy = particle.y - pointer.y;
      const distance = Math.hypot(dx, dy) || 0.01;
      if (distance < interactionRadius) {
        const force = (interactionRadius - distance) / interactionRadius;
        const normalizedX = dx / distance;
        const normalizedY = dy / distance;
        particle.vx += normalizedX * force * REPEL_STRENGTH;
        particle.vy += normalizedY * force * REPEL_STRENGTH;
        particle.vx += -normalizedY * force * SWIRL_STRENGTH;
        particle.vy += normalizedX * force * SWIRL_STRENGTH;
      }
    }

    particle.vx *= FRICTION;
    particle.vy *= FRICTION;
    particle.x += particle.vx;
    particle.y += particle.vy;
  }

  frameNumber += 1;
  if (frameNumber % 30 === 0 && hostRef.value) {
    const currentColor = resolveParticleColor(getComputedStyle(hostRef.value));
    if (currentColor !== renderColor) {
      renderColor = currentColor;
      if (canvasRef.value) canvasRef.value.dataset.renderColor = renderColor;
    }
  }
  drawFrame();
  animationFrame = requestAnimationFrame(animate);
}

function handlePointerMove(event) {
  if (reducedMotionQuery.matches || !hostRef.value) {
    pointer.active = false;
    return;
  }
  const bounds = hostRef.value.getBoundingClientRect();
  const verticalAllowance = Math.min(90, interactionRadius);
  const horizontalAllowance = 36;
  pointer.active =
    event.clientX >= bounds.left - horizontalAllowance &&
    event.clientX <= bounds.right + horizontalAllowance &&
    event.clientY >= bounds.top - verticalAllowance &&
    event.clientY <= bounds.bottom + verticalAllowance;
  if (pointer.active) {
    pointer.x = event.clientX - bounds.left;
    pointer.y = event.clientY - bounds.top;
  }
}

function handlePointerLeave() {
  pointer.active = false;
}

function handleVisibilityChange() {
  cancelAnimationFrame(animationFrame);
  if (!document.hidden) animationFrame = requestAnimationFrame(animate);
}

function scheduleRebuild() {
  window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(rebuildParticles, 140);
}

async function initialize() {
  if (document.fonts?.ready) await document.fonts.ready;
  await nextTick();
  rebuildParticles();
  animationFrame = requestAnimationFrame(animate);
}

onMounted(() => {
  resizeObserver = new ResizeObserver(scheduleRebuild);
  resizeObserver.observe(hostRef.value);

  themeObserver = new MutationObserver(() => {
    if (!hostRef.value) return;
    renderColor = resolveParticleColor(getComputedStyle(hostRef.value));
    if (canvasRef.value) canvasRef.value.dataset.renderColor = renderColor;
  });
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class", "data-personalization", "style"],
  });
  if (document.body) {
    themeObserver.observe(document.body, {
      attributes: true,
      attributeFilter: ["class", "style"],
    });
  }

  window.addEventListener("pointermove", handlePointerMove, { passive: true });
  window.addEventListener("pointerleave", handlePointerLeave, {
    passive: true,
  });
  document.addEventListener("visibilitychange", handleVisibilityChange);
  reducedMotionQuery.addEventListener("change", scheduleRebuild);
  initialize();
});

watch(() => props.text, scheduleRebuild);

onBeforeUnmount(() => {
  destroyed = true;
  cancelAnimationFrame(animationFrame);
  window.clearTimeout(resizeTimer);
  resizeObserver?.disconnect();
  themeObserver?.disconnect();
  window.removeEventListener("pointermove", handlePointerMove);
  window.removeEventListener("pointerleave", handlePointerLeave);
  document.removeEventListener("visibilitychange", handleVisibilityChange);
  reducedMotionQuery.removeEventListener("change", scheduleRebuild);
  particles.length = 0;
});
</script>

<style scoped>
.particle-text {
  position: relative;
  width: min(1280px, calc(100vw - 40px));
  height: 1.18em;
  max-width: 100%;
  isolation: isolate;
  color: var(
    --particle-title-color,
    var(--heading-text-color, var(--app-text-primary))
  );
}

.particle-text__fallback {
  display: grid;
  height: 100%;
  place-items: center;
  font: inherit;
  letter-spacing: inherit;
  line-height: inherit;
  white-space: nowrap;
}

.particle-text--ready .particle-text__fallback {
  visibility: hidden;
}

.particle-text__canvas {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  background: transparent;
  filter: none;
  mix-blend-mode: normal;
  opacity: 1;
  pointer-events: none;
}

.particle-text__sr-only {
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

@media (max-width: 767px) {
  .particle-text {
    width: calc(100vw - 32px);
    height: 1.22em;
  }
}
</style>
