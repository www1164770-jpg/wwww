<template>
  <form ref="searchRoot" class="search-bar" @submit.prevent="submit">
    <div class="engine-picker">
      <button
        type="button"
        class="engine-picker__trigger"
        aria-haspopup="listbox"
        :aria-expanded="engineMenuOpen"
        :aria-controls="engineMenuId"
        :aria-activedescendant="engineActiveDescendant"
        :aria-label="`当前搜索范围：${currentEngine.label}`"
        @click="toggleEngineMenu"
        @keydown="handleEngineTriggerKeydown"
      >
        <span class="engine-picker__label">{{ currentEngine.label }}</span>
        <ChevronDown
          class="engine-picker__chevron"
          :class="{ 'is-open': engineMenuOpen }"
          aria-hidden="true"
        />
      </button>

      <transition name="engine-menu-pop">
        <div
          v-if="engineMenuOpen"
          :id="engineMenuId"
          class="engine-menu"
          role="listbox"
          aria-label="选择搜索范围"
        >
          <button
            v-for="(engine, index) in SEARCH_ENGINES"
            :id="engineOptionId(index)"
            :key="engine.key"
            type="button"
            class="engine-menu__option"
            :class="{
              'is-active': engineActiveIndex === index,
              'is-selected': searchEngine === engine.key,
            }"
            role="option"
            :aria-selected="searchEngine === engine.key"
            @mouseenter="engineActiveIndex = index"
            @click="selectEngine(engine.key)"
          >
            <span>{{ engine.label }}</span>
            <span
              v-if="searchEngine === engine.key"
              class="engine-menu__check"
              aria-hidden="true"
              >✓</span
            >
          </button>
        </div>
      </transition>
    </div>

    <input
      ref="inputRef"
      v-model="keyword"
      class="search-input"
      type="search"
      :placeholder="currentPlaceholder"
      :aria-label="`使用${currentEngine.label}搜索`"
      aria-autocomplete="list"
      :aria-expanded="suggestionsOpen"
      :aria-controls="suggestionsId"
      :aria-activedescendant="activeDescendant"
      autocomplete="off"
      @focus="handleFocus"
      @input="localError = ''"
      @keydown="handleInputKeydown"
    />
    <button
      class="search-button"
      :class="{ 'is-loading': submitting }"
      type="submit"
      :aria-label="`使用${currentEngine.label}搜索`"
    >
      <LoaderCircle v-if="submitting" class="search-button__spinner" />
      <Search v-else />
    </button>

    <transition name="suggestions-pop">
      <div
        v-if="suggestionsOpen"
        :id="suggestionsId"
        class="search-suggestions"
        role="listbox"
        aria-label="搜索建议"
      >
        <template v-if="!normalizedKeyword">
          <section v-if="recentSuggestionItems.length" class="suggestion-section">
            <div class="suggestions-header">
              <span>最近搜索</span>
              <button type="button" @mousedown.prevent @click="clearRecent">
                清空
              </button>
            </div>
            <div class="recent-suggestions-grid">
              <div
                v-for="(item, index) in recentSuggestionItems"
                :id="suggestionOptionId(index)"
                :key="item.key"
                class="suggestion-option suggestion-option--compact"
                :class="{ 'is-active': activeIndex === index }"
                role="option"
                :aria-selected="activeIndex === index"
                @mouseenter="activeIndex = index"
                @mousedown.prevent
                @click="selectSuggestion(item)"
              >
                <Clock aria-hidden="true" />
                <span class="suggestion-option__copy">
                  <span class="suggestion-option__name">{{ item.name }}</span>
                </span>
                <button
                  type="button"
                  class="suggestion-option__remove"
                  :aria-label="`删除最近搜索 ${item.name}`"
                  @mousedown.stop.prevent
                  @click.stop="removeRecent(item.name)"
                >
                  <X aria-hidden="true" />
                </button>
              </div>
            </div>
          </section>

          <section v-if="hotSuggestionItems.length" class="suggestion-section">
            <div class="suggestions-header"><span>热门搜索</span></div>
            <div class="hot-suggestions-grid">
              <div
                v-for="(item, hotIndex) in hotSuggestionItems"
                :id="suggestionOptionId(recentSuggestionItems.length + hotIndex)"
                :key="item.key"
                class="suggestion-option suggestion-option--hot"
                :class="{
                  'is-active':
                    activeIndex === recentSuggestionItems.length + hotIndex,
                }"
                role="option"
                :aria-selected="
                  activeIndex === recentSuggestionItems.length + hotIndex
                "
                @mouseenter="activeIndex = recentSuggestionItems.length + hotIndex"
                @mousedown.prevent
                @click="selectSuggestion(item)"
              >
                <TrendingUp aria-hidden="true" />
                <span class="suggestion-option__name">{{ item.name }}</span>
              </div>
            </div>
          </section>
        </template>

        <div
          v-for="(item, index) in normalizedKeyword ? displayedSuggestions : []"
          v-else
          :id="suggestionOptionId(index)"
          :key="item.key"
          class="suggestion-option"
          :class="{ 'is-active': activeIndex === index }"
          role="option"
          :aria-selected="activeIndex === index"
          @mouseenter="activeIndex = index"
          @mousedown.prevent
          @click="selectSuggestion(item)"
        >
          <SiteLogo
            v-if="item.type === 'site'"
            :name="item.name"
            :url="item.url"
            :logo="item.logoUrl"
            size="sm"
            decorative
          />
          <Folder v-else-if="item.type === 'category'" aria-hidden="true" />
          <Clock v-else-if="item.type === 'recent'" aria-hidden="true" />
          <TrendingUp v-else aria-hidden="true" />

          <span class="suggestion-option__copy">
            <span class="suggestion-option__name">
              <template
                v-for="(segment, segmentIndex) in highlightSegments(
                  item.name,
                  normalizedKeyword,
                )"
                :key="`${item.key}-${segmentIndex}`"
              >
                <mark v-if="segment.matched">{{ segment.text }}</mark>
                <span v-else>{{ segment.text }}</span>
              </template>
            </span>
            <span v-if="suggestionMeta(item)" class="suggestion-option__meta">
              {{ suggestionMeta(item) }}
            </span>
          </span>

          <button
            v-if="item.type === 'recent'"
            type="button"
            class="suggestion-option__remove"
            :aria-label="`删除最近搜索 ${item.name}`"
            @mousedown.stop.prevent
            @click.stop="removeRecent(item.name)"
          >
            <X aria-hidden="true" />
          </button>
        </div>

        <p v-if="suggesting" class="suggestions-status">正在获取建议...</p>
      </div>
    </transition>

    <p v-if="localError" class="search-bar__error" role="alert">
      {{ localError }}
    </p>
  </form>
</template>

<script setup>
import {
  ChevronDown,
  Clock,
  Folder,
  LoaderCircle,
  Search,
  TrendingUp,
  X,
} from "lucide-vue-next";
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import SiteLogo from "../site/SiteLogo.vue";
import { useSearchStore } from "../../stores/search";
import { searchAPI, unwrapResponse } from "../../utils/api";

const SEARCH_DEBOUNCE_MS = 300;
const MAX_SUGGESTIONS = 8;
const SEARCH_ENGINES = Object.freeze([
  { key: "internal", label: "站内搜索", placeholder: "" },
  {
    key: "baidu",
    label: "百度",
    placeholder: "搜索网页内容",
    url: "https://www.baidu.com/s?wd=",
  },
  {
    key: "google",
    label: "Google",
    placeholder: "搜索网页内容",
    url: "https://www.google.com/search?q=",
  },
  {
    key: "bing",
    label: "Bing",
    placeholder: "搜索网页内容",
    url: "https://www.bing.com/search?q=",
  },
  {
    key: "github",
    label: "GitHub",
    placeholder: "搜索代码、项目",
    url: "https://github.com/search?q=",
  },
  {
    key: "stackoverflow",
    label: "Stack Overflow",
    placeholder: "搜索编程问题",
    url: "https://stackoverflow.com/search?q=",
  },
  {
    key: "zhihu",
    label: "知乎",
    placeholder: "搜索知乎内容",
    url: "https://www.zhihu.com/search?q=",
  },
  {
    key: "juejin",
    label: "掘金",
    placeholder: "搜索技术文章",
    url: "https://juejin.cn/search?query=",
  },
  {
    key: "bilibili",
    label: "B站",
    placeholder: "搜索视频内容",
    url: "https://search.bilibili.com/all?keyword=",
  },
]);

const props = defineProps({
  modelValue: { type: String, default: "" },
  placeholder: {
    type: String,
    default: "搜索网站、工具或使用场景，例如：论文写作、编程、PPT、设计",
  },
  navigateOnSubmit: { type: Boolean, default: true },
  submitting: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue", "search", "engine-menu-change"]);
const route = useRoute();
const router = useRouter();
const searchStore = useSearchStore();
const searchRoot = ref(null);
const inputRef = ref(null);
const keyword = ref(props.modelValue);
const searchEngine = ref("internal");
const engineMenuOpen = ref(false);
const engineActiveIndex = ref(0);
const localError = ref("");
const focused = ref(false);
const remoteSuggestions = ref([]);
const recentSearches = ref([]);
const hotKeywords = ref([]);
const suggesting = ref(false);
const activeIndex = ref(-1);
const suggestionsId = `site-search-suggestions-${useId()}`;
const engineMenuId = `search-engine-menu-${useId()}`;
let debounceTimer = null;
let suggestionController = null;
let requestSequence = 0;

const normalizedKeyword = computed(() =>
  String(keyword.value || "")
    .trim()
    .replace(/\s+/g, " "),
);
const currentEngine = computed(
  () =>
    SEARCH_ENGINES.find((engine) => engine.key === searchEngine.value) ||
    SEARCH_ENGINES[0],
);
const currentPlaceholder = computed(
  () => currentEngine.value.placeholder || props.placeholder,
);

const idleSuggestions = computed(() => {
  const recent = recentSearches.value.slice(0, 4).map((name) => ({
    type: "recent",
    name,
    key: `recent:${name.toLocaleLowerCase()}`,
  }));
  const seen = new Set(recent.map((item) => item.name.toLocaleLowerCase()));
  const hot = hotKeywords.value
    .filter((name) => !seen.has(name.toLocaleLowerCase()))
    .slice(0, 6)
    .map((name) => ({
      type: "keyword",
      name,
      key: `hot:${name.toLocaleLowerCase()}`,
    }));
  return [...recent, ...hot];
});

const recentSuggestionItems = computed(() =>
  idleSuggestions.value.filter((item) => item.type === "recent").slice(0, 4),
);
const hotSuggestionItems = computed(() =>
  idleSuggestions.value.filter((item) => item.type === "keyword").slice(0, 6),
);

const displayedSuggestions = computed(() =>
  normalizedKeyword.value
    ? remoteSuggestions.value.slice(0, MAX_SUGGESTIONS)
    : idleSuggestions.value,
);
const suggestionsOpen = computed(
  () =>
    searchEngine.value === "internal" &&
    focused.value &&
    (displayedSuggestions.value.length > 0 || suggesting.value),
);
const activeDescendant = computed(() =>
  activeIndex.value >= 0 ? suggestionOptionId(activeIndex.value) : undefined,
);
const engineActiveDescendant = computed(() =>
  engineMenuOpen.value ? engineOptionId(engineActiveIndex.value) : undefined,
);

watch(
  () => props.modelValue,
  (value) => {
    if (value !== keyword.value) keyword.value = value || "";
  },
);

watch(keyword, (value) => {
  emit("update:modelValue", value || "");
  activeIndex.value = -1;
  scheduleSuggestions();
});

watch([suggestionsOpen, engineMenuOpen], ([suggestions, engines]) =>
  emit("engine-menu-change", suggestions || engines),
);

watch(
  () => props.submitting,
  (submitting) => {
    if (submitting) {
      closeSuggestions();
      closeEngineMenu();
    }
  },
);

watch(
  () => route.fullPath,
  () => {
    closeSuggestions();
    closeEngineMenu();
  },
);

function canRequestSuggestions(value) {
  return /[\u3400-\u9fff]/.test(value) || value.length >= 2;
}

function normalizeSuggestion(item, index) {
  const type = item?.type || "keyword";
  const name = String(item?.name || "").trim();
  return {
    ...item,
    type,
    name,
    logoUrl: item?.logoUrl || item?.logo_url || "",
    categoryName: item?.categoryName || item?.category_name || "",
    key: `${type}:${item?.id ?? item?.code ?? name.toLocaleLowerCase()}:${index}`,
  };
}

function scheduleSuggestions() {
  clearTimeout(debounceTimer);
  suggestionController?.abort();
  suggestionController = null;
  suggesting.value = false;
  const query = normalizedKeyword.value;
  if (
    searchEngine.value !== "internal" ||
    !focused.value ||
    !canRequestSuggestions(query)
  ) {
    remoteSuggestions.value = [];
    return;
  }
  debounceTimer = setTimeout(
    () => void loadSuggestions(query),
    SEARCH_DEBOUNCE_MS,
  );
}

async function loadSuggestions(query) {
  suggestionController?.abort();
  const controller = new AbortController();
  suggestionController = controller;
  const sequence = ++requestSequence;
  suggesting.value = true;
  try {
    const response = await searchAPI.suggest(query, {
      signal: controller.signal,
    });
    if (sequence !== requestSequence || query !== normalizedKeyword.value)
      return;
    const payload = unwrapResponse(response) || {};
    remoteSuggestions.value = (payload.items || [])
      .map(normalizeSuggestion)
      .filter((item) => item.name)
      .slice(0, MAX_SUGGESTIONS);
  } catch (error) {
    if (error?.code !== "ERR_CANCELED" && sequence === requestSequence) {
      remoteSuggestions.value = [];
    }
  } finally {
    if (sequence === requestSequence) suggesting.value = false;
  }
}

async function loadHotKeywords() {
  if (hotKeywords.value.length) return;
  try {
    const response = await searchAPI.hotKeywords();
    const payload = unwrapResponse(response);
    hotKeywords.value = (Array.isArray(payload) ? payload : []).slice(0, 8);
  } catch {
    hotKeywords.value = ["AI编程", "前端框架", "论文写作", "PPT模板"];
  }
}

function handleFocus() {
  focused.value = true;
  if (searchEngine.value !== "internal") return;
  recentSearches.value = searchStore.getRecentSearches();
  void loadHotKeywords();
  scheduleSuggestions();
}

function closeSuggestions() {
  focused.value = false;
  activeIndex.value = -1;
  clearTimeout(debounceTimer);
  suggestionController?.abort();
  suggestionController = null;
  suggesting.value = false;
}

function submitValue(value) {
  const query = String(value || "")
    .trim()
    .replace(/\s+/g, " ");
  if (!query) {
    localError.value = "请输入搜索关键词";
    inputRef.value?.focus();
    return;
  }
  keyword.value = query;
  if (searchEngine.value !== "internal") {
    const target = `${currentEngine.value.url}${encodeURIComponent(query)}`;
    closeSuggestions();
    window.open(target, "_blank", "noopener,noreferrer");
    return;
  }
  recentSearches.value = searchStore.addRecentSearch(query);
  closeSuggestions();
  emit("search", query);
  if (props.navigateOnSubmit) {
    void router.push({ path: "/search", query: { q: query } });
  }
}

function selectEngine(engineKey) {
  const index = SEARCH_ENGINES.findIndex((engine) => engine.key === engineKey);
  if (index < 0) return;
  searchEngine.value = engineKey;
  engineActiveIndex.value = index;
  localError.value = "";
  remoteSuggestions.value = [];
  engineMenuOpen.value = false;
  closeSuggestions();
  inputRef.value?.focus();
}

function openEngineMenu() {
  closeSuggestions();
  engineActiveIndex.value = Math.max(
    0,
    SEARCH_ENGINES.findIndex((engine) => engine.key === searchEngine.value),
  );
  engineMenuOpen.value = true;
}

function closeEngineMenu() {
  engineMenuOpen.value = false;
}

function toggleEngineMenu() {
  if (engineMenuOpen.value) closeEngineMenu();
  else openEngineMenu();
}

function chooseActiveEngine() {
  selectEngine(SEARCH_ENGINES[engineActiveIndex.value]?.key || "internal");
}

function handleEngineTriggerKeydown(event) {
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    if (!engineMenuOpen.value) openEngineMenu();
    else {
      const direction = event.key === "ArrowDown" ? 1 : -1;
      engineActiveIndex.value =
        (engineActiveIndex.value + direction + SEARCH_ENGINES.length) %
        SEARCH_ENGINES.length;
    }
    return;
  }
  if ((event.key === "Enter" || event.key === " ") && engineMenuOpen.value) {
    event.preventDefault();
    chooseActiveEngine();
    return;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    closeEngineMenu();
  }
}

function engineOptionId(index) {
  return `${engineMenuId}-option-${index}`;
}

function submit() {
  submitValue(keyword.value);
}

function selectSuggestion(item) {
  if (item.type === "category") {
    const query = normalizedKeyword.value || item.name;
    recentSearches.value = searchStore.addRecentSearch(query);
    closeSuggestions();
    void router.push({
      path: "/search",
      query: { q: query, category: item.code || item.id },
    });
    return;
  }
  submitValue(item.name);
}

function handleInputKeydown(event) {
  if (event.key === "ArrowDown" && displayedSuggestions.value.length) {
    event.preventDefault();
    activeIndex.value =
      (activeIndex.value + 1) % displayedSuggestions.value.length;
    return;
  }
  if (event.key === "ArrowUp" && displayedSuggestions.value.length) {
    event.preventDefault();
    activeIndex.value =
      activeIndex.value <= 0
        ? displayedSuggestions.value.length - 1
        : activeIndex.value - 1;
    return;
  }
  if (event.key === "Enter" && activeIndex.value >= 0) {
    event.preventDefault();
    selectSuggestion(displayedSuggestions.value[activeIndex.value]);
    return;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    closeSuggestions();
    inputRef.value?.focus();
    return;
  }
  if (event.key === "Tab") closeSuggestions();
}

function suggestionOptionId(index) {
  return `${suggestionsId}-option-${index}`;
}

function suggestionMeta(item) {
  if (item.type === "site") return item.categoryName || "网站";
  if (item.type === "category") return "分类";
  if (item.type === "keyword") return "热门搜索";
  return "";
}

function highlightSegments(value, query) {
  const text = String(value || "");
  const needle = String(query || "").trim();
  if (!needle) return [{ text, matched: false }];
  const source = text.toLocaleLowerCase();
  const target = needle.toLocaleLowerCase();
  const segments = [];
  let cursor = 0;
  while (cursor < text.length) {
    const index = source.indexOf(target, cursor);
    if (index < 0) {
      segments.push({ text: text.slice(cursor), matched: false });
      break;
    }
    if (index > cursor) {
      segments.push({ text: text.slice(cursor, index), matched: false });
    }
    segments.push({
      text: text.slice(index, index + needle.length),
      matched: true,
    });
    cursor = index + needle.length;
  }
  return segments.length ? segments : [{ text, matched: false }];
}

function removeRecent(value) {
  recentSearches.value = searchStore.removeRecentSearch(value);
  activeIndex.value = -1;
}

function clearRecent() {
  recentSearches.value = searchStore.clearRecentSearches();
  activeIndex.value = -1;
}

function handleDocumentPointerDown(event) {
  if (!searchRoot.value?.contains(event.target)) {
    closeSuggestions();
    closeEngineMenu();
  }
}

onMounted(() => {
  document.addEventListener("pointerdown", handleDocumentPointerDown);
});

onBeforeUnmount(() => {
  clearTimeout(debounceTimer);
  suggestionController?.abort();
  document.removeEventListener("pointerdown", handleDocumentPointerDown);
});
</script>

<style scoped>
.search-bar {
  position: relative;
  z-index: 20;
  display: flex;
  width: min(820px, calc(100vw - 40px));
  max-width: 820px;
  min-height: 64px;
  align-items: center;
  margin: 0 auto;
  border: 1px solid var(--app-card-border);
  border-radius: 999px;
  background: var(--app-surface);
  padding: 5px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.12);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.search-bar:focus-within {
  border-color: color-mix(in srgb, var(--color-primary) 55%, transparent);
  box-shadow:
    0 12px 32px rgba(0, 0, 0, 0.16),
    0 0 0 3px color-mix(in srgb, var(--color-primary) 8%, transparent);
}

.engine-picker {
  position: relative;
  flex: 0 0 160px;
  height: 52px;
  margin-left: 2px;
}

.engine-picker__trigger {
  display: flex;
  width: 100%;
  min-width: 0;
  height: 100%;
  min-height: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--app-card-border);
  border-radius: 999px;
  background: var(--app-card-bg);
  color: var(--app-text-secondary);
  padding: 0 18px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.engine-picker__trigger:hover,
.engine-picker__trigger:focus-visible,
.engine-picker__trigger[aria-expanded="true"] {
  border-color: var(--color-primary);
  background: var(--app-card-hover-bg);
  box-shadow: var(--app-control-shadow);
  outline: none;
}

.engine-picker__label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.engine-picker__chevron {
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
  color: #ff7058;
  pointer-events: none;
  transition: transform 0.2s ease;
}

.engine-picker__chevron.is-open {
  transform: rotate(180deg);
}

.engine-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 30;
  display: grid;
  width: 100%;
  height: auto;
  min-width: 0;
  min-height: 0;
  max-width: none;
  max-height: 204px;
  box-sizing: border-box;
  gap: 2px;
  overflow-x: hidden;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  background: #242424;
  padding: 6px;
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.32);
  backdrop-filter: blur(var(--app-blur));
  -webkit-backdrop-filter: blur(var(--app-blur));
  scrollbar-color: rgba(255, 255, 255, 0.16) transparent;
  scrollbar-width: thin;
}

.engine-menu::-webkit-scrollbar {
  width: 6px;
}

.engine-menu::-webkit-scrollbar-track {
  background: transparent;
}

.engine-menu::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
}

.engine-menu__option {
  display: flex;
  width: 100%;
  min-width: 0;
  min-height: 44px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: rgba(255, 255, 255, 0.76);
  padding: 0 14px;
  font-size: 14px;
  font-weight: 500;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;
}

.engine-menu__option:hover,
.engine-menu__option.is-active {
  background: rgba(255, 255, 255, 0.07);
  color: #ffffff;
}

.engine-menu__option.is-selected {
  background: rgba(203, 94, 61, 0.18);
  color: #ffffff;
}

.engine-menu__option:focus-visible {
  outline: 2px solid rgba(255, 112, 88, 0.45);
  outline-offset: -2px;
}

.engine-menu__option > span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
}

.engine-menu__check {
  flex: 0 0 auto;
  color: rgba(255, 255, 255, 0.55);
  font-weight: 850;
}

.engine-menu-pop-enter-active,
.engine-menu-pop-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
  transform-origin: top left;
}

.engine-menu-pop-enter-from,
.engine-menu-pop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}

.search-input {
  flex: 1;
  min-width: 0;
  height: 54px;
  border: 0;
  background: transparent;
  box-shadow: none;
  padding: 0 22px;
  color: var(--app-text-primary);
  outline: 0;
  font-size: 18px;
}

.search-input::placeholder {
  color: var(--app-text-primary);
  opacity: 0.48;
}

.search-input:focus {
  border: 0 !important;
  box-shadow: none !important;
  outline: 0;
}

.search-button {
  display: inline-grid;
  flex: 0 0 52px;
  width: 52px;
  height: 52px;
  min-width: 52px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--app-text-inverse);
  box-shadow: 0 12px 24px rgba(255, 112, 88, 0.2);
  transition:
    transform var(--transition),
    background var(--transition),
    box-shadow var(--transition);
}

.search-button svg {
  width: 21px;
  height: 21px;
}

.search-button:hover,
.search-button:focus-visible {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 16px 30px rgba(255, 112, 88, 0.26);
  outline: none;
}

.search-button__spinner {
  animation: search-spin 0.75s linear infinite;
}

.search-suggestions {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: 30;
  width: 100%;
  max-height: 320px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--app-text-primary) 10%, transparent);
  border-radius: 16px;
  background: color-mix(in srgb, var(--app-surface-strong) 94%, transparent);
  padding: 10px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.suggestion-section + .suggestion-section {
  margin-top: 6px;
  border-top: 1px solid color-mix(in srgb, var(--app-text-primary) 8%, transparent);
  padding-top: 6px;
}

.suggestions-header {
  display: flex;
  min-height: 30px;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  color: var(--app-text-muted);
  font-size: 12px;
  font-weight: 800;
}

.recent-suggestions-grid,
.hot-suggestions-grid {
  display: grid;
  gap: 4px;
}

.recent-suggestions-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.hot-suggestions-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.suggestions-header button {
  border: 0;
  background: transparent;
  color: var(--color-primary-dark);
  padding: 6px;
  font-size: 12px;
}

.suggestion-option {
  display: flex;
  width: 100%;
  min-height: 54px;
  align-items: center;
  gap: 12px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--app-text-primary);
  padding: 7px 10px;
  text-align: left;
}

.suggestion-option--compact,
.suggestion-option--hot {
  min-height: 38px;
  gap: 8px;
  padding: 5px 8px;
  cursor: pointer;
}

.suggestion-option--compact > svg,
.suggestion-option--hot > svg {
  width: 16px;
  height: 16px;
  flex-basis: 16px;
}

.suggestion-option--hot .suggestion-option__name {
  overflow: hidden;
  min-width: 0;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suggestion-option > svg {
  flex: 0 0 22px;
  width: 22px;
  height: 22px;
  color: var(--app-text-secondary);
}

.suggestion-option:hover,
.suggestion-option.is-active {
  background: var(--app-card-hover-bg);
}

.suggestion-option__copy {
  display: grid;
  flex: 1;
  min-width: 0;
  gap: 3px;
}

.suggestion-option__name,
.suggestion-option__meta {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suggestion-option__name {
  font-size: 14px;
  font-weight: 800;
}

.suggestion-option__name mark {
  background: transparent;
  color: var(--color-primary-dark);
}

.suggestion-option__meta {
  color: var(--app-text-secondary);
  font-size: 12px;
}

.suggestion-option__remove {
  display: inline-grid;
  flex: 0 0 26px;
  width: 26px;
  height: 26px;
  place-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--app-text-muted);
}

.suggestion-option__remove:hover,
.suggestion-option__remove:focus-visible {
  background: var(--app-card-hover-bg);
  color: var(--color-primary-dark);
  outline: none;
}

.suggestion-option__remove svg {
  width: 16px;
  height: 16px;
}

.suggestions-status {
  margin: 0;
  padding: 10px;
  color: var(--app-text-muted);
  font-size: 13px;
  text-align: center;
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

.suggestions-pop-enter-active,
.suggestions-pop-leave-active {
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
}

.suggestions-pop-enter-from,
.suggestions-pop-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

@keyframes search-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 560px) {
  .search-bar {
    width: min(820px, calc(100vw - 32px));
    min-height: 60px;
    padding: 4px;
  }

  .engine-picker {
    flex-basis: 124px;
    height: 50px;
  }

  .engine-picker__trigger {
    gap: 8px;
    padding: 0 12px;
    font-size: 13px;
  }

  .engine-menu {
    width: 100%;
    min-width: 0;
    max-width: none;
  }

  .search-input {
    height: 50px;
    padding: 0 10px;
    font-size: 16px;
  }

  .search-button {
    flex-basis: 50px;
    width: 50px;
    height: 50px;
    min-width: 50px;
  }

  .search-suggestions {
    width: calc(100vw - 32px);
    max-height: 320px;
    overflow-y: auto;
  }

  .recent-suggestions-grid,
  .hot-suggestions-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (prefers-reduced-motion: reduce) {
  .engine-menu-pop-enter-active,
  .engine-menu-pop-leave-active,
  .engine-picker__chevron,
  .suggestions-pop-enter-active,
  .suggestions-pop-leave-active,
  .search-button {
    transition: none;
  }
}
</style>
