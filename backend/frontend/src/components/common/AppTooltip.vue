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

    <Transition name="app-tooltip-fade">
      <div
        v-if="visible && canInteract"
        :id="tooltipId"
        class="app-tooltip__content"
        role="tooltip"
      >
        {{ normalizedContent }}
      </div>
    </Transition>
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
});

const triggerElement = ref(null);
const visible = ref(false);
const isOverflowing = ref(false);
const tooltipId = `app-tooltip-${++nextTooltipId}`;

const normalizedContent = computed(() => props.content.trim());
const hasContent = computed(() => Boolean(normalizedContent.value));
const canInteract = computed(
  () =>
    hasContent.value &&
    !props.disabled &&
    (!props.showOnOverflow || isOverflowing.value),
);

function showTooltip() {
  if (canInteract.value) {
    visible.value = true;
  }
}

function hideTooltip() {
  visible.value = false;
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

let resizeObserver;

function observeOverflow() {
  resizeObserver?.disconnect();
  if (!props.showOnOverflow || typeof ResizeObserver === "undefined") {
    updateOverflow();
    return;
  }

  const target = getOverflowTarget();
  if (target) {
    resizeObserver = new ResizeObserver(updateOverflow);
    resizeObserver.observe(target);
  }
  updateOverflow();
}

onMounted(async () => {
  await nextTick();
  observeOverflow();
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
