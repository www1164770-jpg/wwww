<template>
  <div v-if="hasContent && !disabled" class="app-tooltip">
    <div
      ref="triggerElement"
      class="app-tooltip__trigger"
      :tabindex="canInteract ? 0 : undefined"
      :aria-describedby="visible && canInteract ? tooltipId : undefined"
      @mouseenter="showTooltip"
      @mouseleave="hideTooltip"
      @focusin="showTooltip"
      @focusout="handleFocusout"
      @keydown.esc="hideTooltip"
    >
      <slot />
    </div>

    <Teleport to="body" :disabled="!floating">
      <Transition name="app-tooltip-fade">
      <div
        v-if="visible && canInteract"
        ref="tooltipElement"
        :id="tooltipId"
        class="app-tooltip__content"
        :class="{
          'app-tooltip__content--floating': floating,
          'app-tooltip__content--bottom': resolvedPlacement === 'bottom',
        }"
        :style="floatingStyle"
        role="tooltip"
      >
        {{ normalizedContent }}
      </div>
      </Transition>
    </Teleport>
  </div>
  <slot v-else />
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

let nextTooltipId = 0;

const props = defineProps({
  content: { type: String, default: "" },
  disabled: { type: Boolean, default: false },
  showOnOverflow: { type: Boolean, default: false },
  // Category cards opt into a body-level overlay so a clipped card cannot
  // position the complete description over its own header.
  floating: { type: Boolean, default: false },
  placement: { type: String, default: "top" },
  offset: { type: Number, default: 9 },
});

const triggerElement = ref(null);
const tooltipElement = ref(null);
const visible = ref(false);
const isOverflowing = ref(false);
const resolvedPlacement = ref("top");
const isPositioned = ref(false);
const floatingPosition = ref({ top: "0px", left: "0px" });
const tooltipId = `app-tooltip-${++nextTooltipId}`;

const normalizedContent = computed(() => props.content.trim());
const hasContent = computed(() => Boolean(normalizedContent.value));
const canInteract = computed(
  () =>
    hasContent.value &&
    !props.disabled &&
    (!props.showOnOverflow || isOverflowing.value),
);
const floatingStyle = computed(() =>
  props.floating
    ? {
        ...floatingPosition.value,
        visibility: isPositioned.value ? "visible" : "hidden",
      }
    : undefined,
);

async function showTooltip() {
  if (canInteract.value) {
    visible.value = true;
    if (props.floating) {
      isPositioned.value = false;
      await nextTick();
      updateFloatingPosition();
    }
  }
}

function hideTooltip() {
  visible.value = false;
  isPositioned.value = false;
}

function handleFocusout(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    hideTooltip();
  }
}

function getOverflowTarget() {
  return (
    triggerElement.value?.querySelector("[data-tooltip-overflow-target]") ||
    triggerElement.value?.firstElementChild ||
    triggerElement.value
  );
}

function hasOverflow(element) {
  if (!element || !element.clientWidth) return false;

  const clone = element.cloneNode(true);
  clone.setAttribute("aria-hidden", "true");
  clone.style.position = "absolute";
  clone.style.visibility = "hidden";
  clone.style.pointerEvents = "none";
  clone.style.display = "block";
  clone.style.width = `${element.clientWidth}px`;
  clone.style.height = "auto";
  clone.style.maxHeight = "none";
  clone.style.overflow = "visible";
  clone.style.webkitLineClamp = "unset";
  document.body.appendChild(clone);
  const fullHeight = clone.scrollHeight;
  clone.remove();

  return fullHeight > element.clientHeight + 1;
}

function updateOverflow() {
  if (!props.showOnOverflow) {
    isOverflowing.value = true;
    return;
  }

  const element = getOverflowTarget();
  isOverflowing.value = hasOverflow(element);
  if (!isOverflowing.value) {
    hideTooltip();
  }
}

function updateFloatingPosition() {
  if (!props.floating || !visible.value || !triggerElement.value || !tooltipElement.value) {
    return;
  }

  const triggerRect = triggerElement.value.getBoundingClientRect();
  const categoryCard = triggerElement.value.closest(".website-card--category");
  // Keep the hover target narrow (the description), while anchoring a category
  // tooltip outside the whole card so it can never cover its logo or title.
  const anchorRect = categoryCard?.getBoundingClientRect() || triggerRect;
  const tooltipRect = tooltipElement.value.getBoundingClientRect();
  const viewportPadding = 8;
  const offset = Math.max(8, Number(props.offset) || 9);
  const prefersTop = props.placement !== "bottom";
  const topSpace = anchorRect.top - offset;
  const shouldPlaceTop = prefersTop && topSpace >= tooltipRect.height;
  const placement = shouldPlaceTop ? "top" : "bottom";
  const rawTop =
    placement === "top"
      ? anchorRect.top - tooltipRect.height - offset
      : anchorRect.bottom + offset;
  const left = Math.min(
    Math.max(
      viewportPadding,
      anchorRect.left + anchorRect.width / 2 - tooltipRect.width / 2,
    ),
    Math.max(viewportPadding, window.innerWidth - tooltipRect.width - viewportPadding),
  );

  resolvedPlacement.value = placement;
  floatingPosition.value = {
    top: `${Math.max(viewportPadding, rawTop)}px`,
    left: `${left}px`,
  };
  isPositioned.value = true;
}

function handleViewportChange() {
  updateFloatingPosition();
}

let resizeObserver;

function observeOverflow() {
  resizeObserver?.disconnect();
  if (!props.showOnOverflow || typeof ResizeObserver === "undefined") {
    updateOverflow();
    return;
  }

  const target = getOverflowTarget();
  if (target) {
    resizeObserver = new ResizeObserver(() => {
      updateOverflow();
      updateFloatingPosition();
    });
    resizeObserver.observe(target);
  }
  updateOverflow();
}

onMounted(async () => {
  await nextTick();
  observeOverflow();
  window.addEventListener("resize", handleViewportChange);
  window.addEventListener("scroll", handleViewportChange, true);
});

watch(
  () => [props.content, props.disabled, props.showOnOverflow],
  async () => {
    hideTooltip();
    await nextTick();
    observeOverflow();
  },
);

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  window.removeEventListener("resize", handleViewportChange);
  window.removeEventListener("scroll", handleViewportChange, true);
});
</script>

<style scoped>
.app-tooltip {
  position: relative;
  display: block;
  width: 100%;
  min-width: 0;
}

.app-tooltip__trigger {
  display: block;
  min-width: 0;
}

.app-tooltip__trigger:focus-visible {
  border-radius: 8px;
  outline: 3px solid rgba(255, 112, 88, 0.28);
  outline-offset: 3px;
}

.app-tooltip__content {
  position: absolute;
  z-index: 50;
  bottom: calc(100% + 10px);
  left: 50%;
  width: max-content;
  max-width: min(320px, calc(100vw - 32px));
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.94);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);
  color: #f8fafc;
  padding: 10px 12px;
  pointer-events: none;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.65;
  text-align: left;
  white-space: normal;
  overflow-wrap: anywhere;
  transform: translateX(-50%);
}

.app-tooltip__content--floating {
  position: fixed;
  bottom: auto;
  z-index: 1000;
  min-width: min(180px, calc(100vw - 16px));
  max-width: min(260px, calc(100vw - 16px));
  padding: 8px 10px;
  line-height: 1.5;
  transform: none;
}

.app-tooltip__content--floating::after {
  top: 100%;
  border-top-color: rgba(15, 23, 42, 0.94);
  border-bottom-color: transparent;
}

.app-tooltip__content--floating.app-tooltip__content--bottom::after {
  top: auto;
  bottom: 100%;
  border-top-color: transparent;
  border-bottom-color: rgba(15, 23, 42, 0.94);
}

.app-tooltip__content--floating.app-tooltip-fade-enter-from,
.app-tooltip__content--floating.app-tooltip-fade-leave-to {
  transform: none;
}

.app-tooltip__content::after {
  position: absolute;
  top: 100%;
  left: 50%;
  border: 5px solid transparent;
  border-top-color: rgba(15, 23, 42, 0.94);
  content: "";
  transform: translateX(-50%);
}

.app-tooltip-fade-enter-active,
.app-tooltip-fade-leave-active {
  transition:
    opacity 140ms ease,
    transform 140ms ease;
}

.app-tooltip-fade-enter-from,
.app-tooltip-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 4px);
}

@media (hover: none), (pointer: coarse) {
  .app-tooltip__content {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-tooltip-fade-enter-active,
  .app-tooltip-fade-leave-active {
    transition: opacity 100ms linear;
  }

  .app-tooltip-fade-enter-from,
  .app-tooltip-fade-leave-to {
    transform: translateX(-50%);
  }
}
</style>
