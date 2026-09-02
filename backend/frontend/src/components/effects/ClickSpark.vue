<template>
  <canvas
    ref="canvasRef"
    class="click-spark-canvas"
    aria-hidden="true"
  ></canvas>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { usePersonalizationStore } from "../../stores/personalization";
import { relativeLuminance } from "../../utils/personalization";

const props = defineProps({
  colorMode: {
    type: String,
    default: "auto",
    validator: (value) => ["auto", "fixed"].includes(value),
  },
  fixedColor: {
    type: String,
    default: "#FFFFFF",
  },
  sparkSize: {
    type: Number,
    default: 15,
  },
  sparkRadius: {
    type: Number,
    default: 60,
  },
  sparkCount: {
    type: Number,
    default: 11,
  },
  duration: {
    type: Number,
    default: 500,
  },
  extraScale: {
    type: Number,
    default: 0.9,
  },
});

const personalizationStore = usePersonalizationStore();
const canvasRef = ref(null);
const sparks = [];
const dragThreshold = 6;
const darkSparkColor = "#111827";
const lightSparkColor = "#FFFFFF";
const luminanceThreshold = 0.45;
const minimumContrastRatio = 3;
const darkSparkLuminance = relativeLuminance(darkSparkColor);
const lightSparkLuminance = relativeLuminance(lightSparkColor);

let context = null;
let animationFrameId = null;
let resizeFrameId = null;
let viewportWidth = 0;
let viewportHeight = 0;
let reducedMotionQuery = null;
let pointerOrigin = null;
let pointerDragged = false;
let dragResetTimeoutId = null;

function resizeCanvas() {
  const canvas = canvasRef.value;
  if (!canvas || !context) return;

  const dpr = window.devicePixelRatio || 1;
  const bounds = canvas.getBoundingClientRect();
  viewportWidth = bounds.width || window.innerWidth;
  viewportHeight = bounds.height || window.innerHeight;
  canvas.width = Math.round(viewportWidth * dpr);
  canvas.height = Math.round(viewportHeight * dpr);
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function handleResize() {
  resizeCanvas();

  if (resizeFrameId !== null) {
    window.cancelAnimationFrame(resizeFrameId);
  }

  resizeFrameId = window.requestAnimationFrame(() => {
    resizeFrameId = null;
    resizeCanvas();
  });
}

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function parseCssColor(value) {
  const source = String(value || "").trim();
  if (!source || source === "transparent") return null;

  if (source.startsWith("#")) {
    const hex = source.slice(1);
    const expanded =
      hex.length === 3 || hex.length === 4
        ? [...hex].map((part) => part + part).join("")
        : hex;

    if (![6, 8].includes(expanded.length) || !/^[\da-f]+$/i.test(expanded)) {
      return null;
    }

    return {
      r: Number.parseInt(expanded.slice(0, 2), 16),
      g: Number.parseInt(expanded.slice(2, 4), 16),
      b: Number.parseInt(expanded.slice(4, 6), 16),
      a:
        expanded.length === 8
          ? Number.parseInt(expanded.slice(6, 8), 16) / 255
          : 1,
    };
  }

  if (!/^rgba?\(/i.test(source)) return null;

  const parts = source
    .slice(source.indexOf("(") + 1, -1)
    .replace("/", " ")
    .split(/[\s,]+/)
    .filter(Boolean);

  if (parts.length < 3) return null;

  const channel = (part) =>
    clamp(
      part.endsWith("%")
        ? (Number.parseFloat(part) / 100) * 255
        : Number.parseFloat(part),
      0,
      255,
    );
  const alpha = (part = "1") =>
    clamp(
      part.endsWith("%")
        ? Number.parseFloat(part) / 100
        : Number.parseFloat(part),
      0,
      1,
    );
  const color = {
    r: channel(parts[0]),
    g: channel(parts[1]),
    b: channel(parts[2]),
    a: alpha(parts[3]),
  };

  return Object.values(color).every(Number.isFinite) ? color : null;
}

function srgbToLinear(value) {
  const channel = value / 255;
  return channel <= 0.04045
    ? channel / 12.92
    : ((channel + 0.055) / 1.055) ** 2.4;
}

function getLuminance(color) {
  return (
    0.2126 * srgbToLinear(color.r) +
    0.7152 * srgbToLinear(color.g) +
    0.0722 * srgbToLinear(color.b)
  );
}

function neutralColorForLuminance(luminance) {
  const linear = clamp(Number(luminance) || 0, 0, 1);
  const srgb =
    linear <= 0.0031308 ? linear * 12.92 : 1.055 * linear ** (1 / 2.4) - 0.055;
  const channel = Math.round(clamp(srgb, 0, 1) * 255);
  return { r: channel, g: channel, b: channel, a: 1 };
}

function compositeColor(foreground, background) {
  const alpha = foreground.a + background.a * (1 - foreground.a);
  if (alpha <= 0) return { r: 0, g: 0, b: 0, a: 0 };

  return {
    r:
      (foreground.r * foreground.a +
        background.r * background.a * (1 - foreground.a)) /
      alpha,
    g:
      (foreground.g * foreground.a +
        background.g * background.a * (1 - foreground.a)) /
      alpha,
    b:
      (foreground.b * foreground.a +
        background.b * background.a * (1 - foreground.a)) /
      alpha,
    a: alpha,
  };
}

function compositeLayers(base, layers) {
  let color = base;

  for (let index = layers.length - 1; index >= 0; index -= 1) {
    color = compositeColor(layers[index], color);
  }

  return color;
}

function estimateGradientColor(backgroundImage) {
  if (!/gradient\(/i.test(backgroundImage)) return null;

  const colors = (
    backgroundImage.match(/rgba?\([^)]*\)|#[\da-f]{3,8}\b/gi) || []
  )
    .map(parseCssColor)
    .filter((color) => color && color.a > 0);

  if (colors.length === 0) return null;

  return colors.reduce(
    (average, color) => ({
      r: average.r + color.r / colors.length,
      g: average.g + color.g / colors.length,
      b: average.b + color.b / colors.length,
      a: average.a + color.a / colors.length,
    }),
    { r: 0, g: 0, b: 0, a: 0 },
  );
}

function resolveThemeBackground() {
  const analysis = personalizationStore.backgroundAnalysis;
  const average = Number(analysis?.average);

  if (Number.isFinite(average)) {
    return neutralColorForLuminance(average);
  }

  if (analysis?.recommendedTextMode) {
    return neutralColorForLuminance(
      analysis.recommendedTextMode === "dark" ? 0.85 : 0.08,
    );
  }

  const rootStyle = window.getComputedStyle(document.documentElement);
  const themeText =
    parseCssColor(rootStyle.getPropertyValue("--heading-text-color")) ||
    parseCssColor(rootStyle.getPropertyValue("--app-text-primary"));

  if (themeText) {
    return neutralColorForLuminance(
      getLuminance(themeText) > 0.5 ? 0.08 : 0.85,
    );
  }

  return neutralColorForLuminance(
    window.matchMedia("(prefers-color-scheme: dark)").matches ? 0.08 : 0.85,
  );
}

function resolveVisibleBackground(target) {
  const translucentLayers = [];
  const themeBackground = resolveThemeBackground();
  let element = target instanceof Element ? target : target?.parentElement;

  while (element) {
    const style = window.getComputedStyle(element);
    const backgroundColor = parseCssColor(style.backgroundColor);
    const backgroundImage = style.backgroundImage;

    if (backgroundImage && backgroundImage !== "none") {
      const isThemeRoot =
        element === document.documentElement ||
        element === document.body ||
        element.id === "app";
      const gradientColor = isThemeRoot
        ? null
        : estimateGradientColor(backgroundImage);
      const base = gradientColor
        ? compositeColor(
            gradientColor,
            backgroundColor?.a > 0
              ? compositeColor(backgroundColor, themeBackground)
              : themeBackground,
          )
        : themeBackground;

      return compositeLayers(base, translucentLayers);
    }

    if (backgroundColor?.a > 0) {
      if (backgroundColor.a >= 0.995) {
        return compositeLayers({ ...backgroundColor, a: 1 }, translucentLayers);
      }

      translucentLayers.push(backgroundColor);
    }

    element = element.parentElement;
  }

  return compositeLayers(themeBackground, translucentLayers);
}

function getContrastRatio(colorLuminance, backgroundLuminance) {
  const lighter = Math.max(colorLuminance, backgroundLuminance);
  const darker = Math.min(colorLuminance, backgroundLuminance);
  return (lighter + 0.05) / (darker + 0.05);
}

function resolveSparkColor(target) {
  if (props.colorMode === "fixed") return props.fixedColor;

  const backgroundLuminance = getLuminance(resolveVisibleBackground(target));
  const useDarkSpark = backgroundLuminance > luminanceThreshold;
  const preferredColor = useDarkSpark ? darkSparkColor : lightSparkColor;
  const alternateColor = useDarkSpark ? lightSparkColor : darkSparkColor;
  const preferredLuminance = useDarkSpark
    ? darkSparkLuminance
    : lightSparkLuminance;
  const alternateLuminance = useDarkSpark
    ? lightSparkLuminance
    : darkSparkLuminance;
  const preferredContrast = getContrastRatio(
    preferredLuminance,
    backgroundLuminance,
  );
  const alternateContrast = getContrastRatio(
    alternateLuminance,
    backgroundLuminance,
  );

  return preferredContrast >= minimumContrastRatio ||
    preferredContrast >= alternateContrast
    ? preferredColor
    : alternateColor;
}

function drawFrame(now) {
  context.clearRect(0, 0, viewportWidth, viewportHeight);
  context.lineWidth = 2;
  context.lineCap = "butt";

  for (let index = sparks.length - 1; index >= 0; index -= 1) {
    const spark = sparks[index];
    const elapsed = now - spark.startTime;

    if (elapsed >= props.duration) {
      sparks.splice(index, 1);
      continue;
    }

    const progress = Math.min(Math.max(elapsed / props.duration, 0), 1);
    const eased = progress * (2 - progress);
    const distance = eased * props.sparkRadius * props.extraScale;
    const lineLength = props.sparkSize * (1 - eased);
    const cos = Math.cos(spark.angle);
    const sin = Math.sin(spark.angle);
    const x1 = spark.x + distance * cos;
    const y1 = spark.y + distance * sin;
    const x2 = spark.x + (distance + lineLength) * cos;
    const y2 = spark.y + (distance + lineLength) * sin;

    context.strokeStyle = spark.color;
    context.beginPath();
    context.moveTo(x1, y1);
    context.lineTo(x2, y2);
    context.stroke();
  }

  if (sparks.length > 0) {
    animationFrameId = window.requestAnimationFrame(drawFrame);
  } else {
    animationFrameId = null;
  }
}

function clearDragResetTimeout() {
  if (dragResetTimeoutId !== null) {
    window.clearTimeout(dragResetTimeoutId);
    dragResetTimeoutId = null;
  }
}

function handlePointerDown(event) {
  if (!event.isPrimary || event.button !== 0) return;

  clearDragResetTimeout();
  pointerOrigin = {
    pointerId: event.pointerId,
    x: event.clientX,
    y: event.clientY,
  };
  pointerDragged = false;
}

function handlePointerMove(event) {
  if (!pointerOrigin || event.pointerId !== pointerOrigin.pointerId) return;

  const offsetX = event.clientX - pointerOrigin.x;
  const offsetY = event.clientY - pointerOrigin.y;

  if (offsetX * offsetX + offsetY * offsetY > dragThreshold * dragThreshold) {
    pointerDragged = true;
  }
}

function handlePointerUp(event) {
  if (!pointerOrigin || event.pointerId !== pointerOrigin.pointerId) return;

  pointerOrigin = null;

  if (pointerDragged) {
    clearDragResetTimeout();
    dragResetTimeoutId = window.setTimeout(() => {
      pointerDragged = false;
      dragResetTimeoutId = null;
    }, 0);
  }
}

function handlePointerCancel(event) {
  if (!pointerOrigin || event.pointerId !== pointerOrigin.pointerId) return;

  pointerOrigin = null;
  pointerDragged = false;
  clearDragResetTimeout();
}

function handleClick(event) {
  if (pointerDragged) {
    pointerDragged = false;
    clearDragResetTimeout();
    return;
  }

  if (event.button !== 0 || event.detail === 0 || reducedMotionQuery?.matches) {
    return;
  }

  const startTime = performance.now();
  const color = resolveSparkColor(event.target);

  for (let index = 0; index < props.sparkCount; index += 1) {
    sparks.push({
      x: event.clientX,
      y: event.clientY,
      angle: (2 * Math.PI * index) / props.sparkCount,
      startTime,
      color,
    });
  }

  if (animationFrameId === null) {
    animationFrameId = window.requestAnimationFrame(drawFrame);
  }
}

onMounted(() => {
  context = canvasRef.value.getContext("2d");
  reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  resizeCanvas();
  window.addEventListener("pointerdown", handlePointerDown, true);
  window.addEventListener("pointermove", handlePointerMove, true);
  window.addEventListener("pointerup", handlePointerUp, true);
  window.addEventListener("pointercancel", handlePointerCancel, true);
  window.addEventListener("click", handleClick, true);
  window.addEventListener("resize", handleResize);
  window.visualViewport?.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("pointerdown", handlePointerDown, true);
  window.removeEventListener("pointermove", handlePointerMove, true);
  window.removeEventListener("pointerup", handlePointerUp, true);
  window.removeEventListener("pointercancel", handlePointerCancel, true);
  window.removeEventListener("click", handleClick, true);
  window.removeEventListener("resize", handleResize);
  window.visualViewport?.removeEventListener("resize", handleResize);
  clearDragResetTimeout();

  if (animationFrameId !== null) {
    window.cancelAnimationFrame(animationFrameId);
  }

  if (resizeFrameId !== null) {
    window.cancelAnimationFrame(resizeFrameId);
  }

  sparks.length = 0;
  animationFrameId = null;
  resizeFrameId = null;
  context = null;
  reducedMotionQuery = null;
  pointerOrigin = null;
  pointerDragged = false;
});
</script>

<style scoped>
.click-spark-canvas {
  position: fixed;
  z-index: 2147483647;
  inset: 0;
  display: block;
  width: 100vw;
  height: 100vh;
  height: 100dvh;
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .click-spark-canvas {
    display: none;
  }
}
</style>
