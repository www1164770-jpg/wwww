<template>
  <form class="search-bar" @submit.prevent="submit">
    <div ref="enginePickerRef" class="engine-picker">
      <button
        type="button"
        class="engine-picker__button"
        :class="{ 'is-open': engineOpen }"
        aria-label="选择搜索引擎"
        :aria-expanded="engineOpen"
        aria-haspopup="listbox"
        @click="toggleEngineMenu"
      >
        <span>{{ selectedEngineLabel }}</span>
        <span class="engine-picker__chevron" aria-hidden="true">⌄</span>
      </button>

      <transition name="engine-pop">
        <div
          v-if="engineOpen"
          class="engine-picker__menu"
          role="listbox"
          aria-label="搜索引擎"
        >
          <button
            v-for="engine in searchEngines"
            :key="engine.key"
            type="button"
            class="engine-picker__option"
            :class="{ 'is-active': selectedEngine === engine.key }"
            role="option"
            :aria-selected="selectedEngine === engine.key"
            @click="selectEngine(engine.key)"
          >
            <span
              v-if="selectedEngine === engine.key"
              class="engine-option__arrow"
              aria-hidden="true"
            >
              ➜
            </span>
            <span
              v-else
              class="engine-option__arrow-placeholder"
              aria-hidden="true"
            ></span>
            <span>{{ engine.name }}</span>
          </button>
        </div>
      </transition>
    </div>

    <input
      v-model.trim="keyword"
      class="search-input"
      type="search"
      :placeholder="placeholder"
      aria-label="搜索关键词"
      @input="localError = ''"
    />
    <button class="search-button" type="submit" aria-label="搜索">搜索</button>
    <p v-if="localError" class="search-bar__error">{{ localError }}</p>
  </form>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

const searchEngines = [
  { key: "internal", name: "站内" },
  { key: "google", name: "Google", url: "https://www.google.com/search?q=" },
  { key: "bing", name: "必应", url: "https://www.bing.com/search?q=" },
  { key: "baidu", name: "百度", url: "https://www.baidu.com/s?wd=" },
  { key: "duckduckgo", name: "DuckDuckGo", url: "https://duckduckgo.com/?q=" },
  { key: "sogou", name: "搜狗", url: "https://www.sogou.com/web?query=" },
  { key: "so", name: "360", url: "https://www.so.com/s?q=" },
];

const props = defineProps({
  modelValue: { type: String, default: "" },
  placeholder: {
    type: String,
    default: "搜索 AI 工具、分类、标签...",
  },
  navigateOnSubmit: { type: Boolean, default: true },
  defaultEngine: { type: String, default: "internal" },
});
const emit = defineEmits(["update:modelValue", "search"]);
const router = useRouter();
const keyword = ref(props.modelValue);
const selectedEngine = ref(props.defaultEngine || "internal");
const engineOpen = ref(false);
const enginePickerRef = ref(null);
const localError = ref("");
const selectedEngineLabel = computed(
  () =>
    searchEngines.find((item) => item.key === selectedEngine.value)?.name ||
    "站内",
);

watch(
  () => props.modelValue,
  (value) => {
    keyword.value = value || "";
  },
);

watch(
  () => props.defaultEngine,
  (value) => {
    selectedEngine.value = value || "internal";
  },
);

watch(keyword, (value) => emit("update:modelValue", value || ""));

function toggleEngineMenu() {
  engineOpen.value = !engineOpen.value;
}

function selectEngine(engineKey) {
  selectedEngine.value = engineKey || "internal";
  engineOpen.value = false;
}

function closeEngineMenu() {
  engineOpen.value = false;
}

function handleDocumentClick(event) {
  if (!engineOpen.value) return;
  if (!enginePickerRef.value?.contains(event.target)) {
    closeEngineMenu();
  }
}

function handleDocumentKeydown(event) {
  if (event.key === "Escape") {
    closeEngineMenu();
  }
}

function submit() {
  const value = (keyword.value || "").trim();
  if (!value) {
    localError.value = "请输入搜索关键词";
    return;
  }

  const engine = searchEngines.find(
    (item) => item.key === selectedEngine.value,
  );
  if (!engine || engine.key === "internal") {
    emit("search", value);
    if (props.navigateOnSubmit) {
      router.push({ path: "/search", query: { q: value } });
    }
    return;
  }

  window.open(
    `${engine.url}${encodeURIComponent(value)}`,
    "_blank",
    "noopener,noreferrer",
  );
}

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  document.addEventListener("keydown", handleDocumentKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
  document.removeEventListener("keydown", handleDocumentKeydown);
});
</script>

<style scoped>
.search-bar {
  position: relative;
  display: flex;
  width: min(680px, calc(100vw - 32px));
  max-width: 680px;
  min-height: 62px;
  align-items: center;
  gap: 10px;
  margin: 0 auto;
  border: 1px solid rgba(226, 232, 240, 0.88);
  border-radius: 999px;
  background: #ffffff;
  padding: 8px;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.search-bar:focus-within {
  border-color: rgba(255, 112, 88, 0.46);
  box-shadow: 0 18px 46px rgba(255, 112, 88, 0.15);
}

.engine-picker {
  position: relative;
  flex: 0 0 auto;
}

.engine-picker__button {
  height: 44px;
  min-width: 104px;
  border: 1px solid rgba(255, 112, 88, 0.22);
  border-radius: 999px;
  background: #fff7f4;
  color: #253044;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 14px 0 18px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition:
    border-color var(--transition),
    box-shadow var(--transition),
    background var(--transition);
}

.engine-picker__button:hover,
.engine-picker__button.is-open,
.engine-picker__button:focus-visible {
  border-color: #ff7058;
  background: #fff1ec;
  box-shadow: 0 10px 24px rgba(255, 112, 88, 0.14);
  outline: none;
}

.engine-picker__chevron {
  color: #ff7058;
  transition: transform 0.2s ease;
}

.engine-picker__button.is-open .engine-picker__chevron {
  transform: rotate(180deg);
}

.engine-picker__menu {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  z-index: 50;
  min-width: 150px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 18px;
  background: #ffffff;
  padding: 8px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.14);
}

.engine-picker__option {
  display: flex;
  width: 100%;
  height: 38px;
  align-items: center;
  gap: 8px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  color: #253044;
  padding: 0 10px;
  text-align: left;
  font-weight: 700;
  cursor: pointer;
}

.engine-picker__option:hover,
.engine-picker__option.is-active,
.engine-picker__option:focus-visible {
  background: #fff4f0;
  color: #ff7058;
  outline: none;
}

.engine-option__arrow,
.engine-option__arrow-placeholder {
  display: inline-flex;
  width: 18px;
  justify-content: center;
  color: #ff7058;
}

.engine-pop-enter-active,
.engine-pop-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.engine-pop-enter-from,
.engine-pop-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.search-input {
  flex: 1 1 auto;
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 0 8px;
  color: var(--color-heading);
  outline: 0;
  font-size: 15px;
}

.search-button {
  flex: 0 0 auto;
  align-self: center;
  width: 52px;
  height: 52px;
  min-width: 52px;
  border: 0;
  border-radius: 50%;
  background: var(--color-primary);
  color: #ffffff;
  font-size: 0;
  box-shadow: 0 12px 24px rgba(255, 112, 88, 0.2);
  transition:
    transform var(--transition),
    background var(--transition),
    box-shadow var(--transition);
}

.search-button:hover,
.search-button:focus-visible {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 16px 30px rgba(255, 112, 88, 0.26);
  outline: none;
}

.search-button::before {
  content: "";
  display: block;
  width: 16px;
  height: 16px;
  margin: 0 auto;
  border: 2px solid currentColor;
  border-radius: 50%;
  box-shadow: 8px 8px 0 -6px currentColor;
  transform: rotate(-15deg);
}

.search-bar__error {
  position: absolute;
  top: calc(100% + 8px);
  left: 22px;
  margin: 0;
  color: var(--color-primary-dark);
  font-size: 13px;
  font-weight: 750;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

@media (max-width: 560px) {
  .search-bar {
    width: calc(100vw - 32px);
    min-height: 58px;
    gap: 8px;
    padding: 7px;
  }

  .engine-picker__button {
    min-width: 92px;
    padding: 0 12px;
    font-size: 13px;
  }

  .search-input {
    padding: 0 4px;
    font-size: 14px;
  }

  .search-button {
    width: 46px;
    height: 46px;
    min-width: 46px;
  }
}

@media (max-width: 420px) {
  .search-bar {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    border-radius: 24px;
  }

  .engine-picker {
    grid-column: 1 / -1;
    width: 100%;
  }

  .engine-picker__button {
    width: 100%;
  }

  .engine-picker__menu {
    width: 100%;
  }
}
</style>
