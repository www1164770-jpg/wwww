<template>
  <form class="search-bar" @submit.prevent="submit">
    <label class="engine-select-wrap">
      <span class="sr-only">搜索引擎</span>
      <select v-model="selectedEngine" aria-label="选择搜索引擎">
        <option
          v-for="engine in searchEngines"
          :key="engine.key"
          :value="engine.key"
        >
          {{ engine.name }}
        </option>
      </select>
    </label>

    <input
      v-model.trim="keyword"
      type="search"
      :placeholder="placeholder"
      aria-label="搜索关键词"
      @input="localError = ''"
    />
    <button type="submit" aria-label="搜索">搜索</button>
    <p v-if="localError" class="search-bar__error">{{ localError }}</p>
  </form>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";

const searchEngines = [
  { key: "internal", name: "站内" },
  { key: "google", name: "Google", url: "https://www.google.com/search?q=" },
  { key: "bing", name: "必应", url: "https://www.bing.com/search?q=" },
  { key: "baidu", name: "百度", url: "https://www.baidu.com/s?wd=" },
  { key: "duckduckgo", name: "DuckDuckGo", url: "https://duckduckgo.com/?q=" },
  { key: "sogou", name: "搜狗", url: "https://www.sogou.com/web?query=" },
  { key: "so", name: "360 搜索", url: "https://www.so.com/s?q=" },
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
const localError = ref("");

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
</script>

<style scoped>
.search-bar {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  width: 100%;
  min-height: 62px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: #ffffff;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.07);
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.search-bar:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 18px 45px rgba(255, 112, 88, 0.16);
}

.engine-select-wrap {
  display: grid;
  align-items: center;
  min-width: 112px;
  border-right: 1px solid var(--color-border-soft);
  padding-left: 18px;
}

select {
  width: 100%;
  min-height: 44px;
  border: 0;
  background: transparent;
  color: var(--color-heading);
  padding: 0 24px 0 0;
  font-size: 14px;
  font-weight: 800;
  outline: none;
}

input {
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 0 10px 0 18px;
  color: var(--color-heading);
  outline: 0;
}

button {
  align-self: center;
  width: 52px;
  height: 52px;
  min-width: 52px;
  margin-right: 5px;
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

button:hover,
button:focus-visible {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 16px 30px rgba(255, 112, 88, 0.26);
  outline: none;
}

button::before {
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
    grid-template-columns: minmax(0, 1fr) auto;
    min-height: 56px;
    border-radius: 24px;
  }

  .engine-select-wrap {
    grid-column: 1 / -1;
    min-width: 0;
    border-right: 0;
    border-bottom: 1px solid var(--color-border-soft);
    padding: 8px 18px 4px;
  }

  select {
    min-height: 36px;
  }

  input {
    padding-left: 18px;
    font-size: 14px;
  }

  button {
    width: 46px;
    height: 46px;
    min-width: 46px;
  }
}
</style>
