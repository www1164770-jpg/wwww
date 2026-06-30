<template>
  <article class="tool-card">
    <div class="tool-head">
      <img :src="logoUrl" :alt="site.name" @error="handleIconError" />
      <div>
        <h3>{{ site.name }}</h3>
        <p>
          {{
            site.desc || site.description || "快速直达常用 AI 工具与效率网站。"
          }}
        </p>
      </div>
    </div>

    <div class="meta">
      <span v-for="tag in normalizedTags" :key="tag">{{ tag }}</span>
    </div>

    <p class="audience">适合：{{ normalizedAudiences.join("、") }}</p>

    <div class="actions">
      <button
        type="button"
        class="ghost"
        @click="$emit('toggle-favorite', site)"
      >
        {{ isFavorited ? "已收藏" : "收藏" }}
      </button>
      <button type="button" @click="$emit('visit', site)">访问网站</button>
    </div>
  </article>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  site: {
    type: Object,
    required: true,
  },
  isFavorited: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["visit", "toggle-favorite"]);

const iconFailed = ref(false);

const domain = computed(() => {
  try {
    return new URL(props.site.url).hostname;
  } catch {
    return "";
  }
});

const logoUrl = computed(() => {
  if (iconFailed.value || !domain.value)
    return `https://api.dicebear.com/8.x/initials/svg?seed=${encodeURIComponent(props.site.name)}`;
  return (
    props.site.logo_url ||
    `https://www.google.com/s2/favicons?domain=${domain.value}&sz=64`
  );
});

const normalizedTags = computed(() => {
  const tags = props.site.tags?.length
    ? props.site.tags
    : [props.site.categoryName || "AI 工具"];
  return tags.slice(0, 3);
});

const normalizedAudiences = computed(() => {
  const audiences = props.site.audiences?.length
    ? props.site.audiences
    : ["学生", "程序员", "运营"];
  return audiences.slice(0, 3);
});

const handleIconError = () => {
  iconFailed.value = true;
};
</script>

<style scoped>
.tool-card {
  display: grid;
  gap: 16px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  padding: 18px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(31, 53, 84, 0.08);
}

.tool-head {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 12px;
  align-items: start;
}

img {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: #edf3fa;
}

h3,
p {
  margin: 0;
}

h3 {
  color: #18212f;
  font-size: 18px;
}

.tool-head p,
.audience {
  margin-top: 6px;
  color: #64748b;
  line-height: 1.55;
  font-size: 14px;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta span {
  border-radius: 999px;
  padding: 5px 9px;
  color: #1769aa;
  background: #e9f4fc;
  font-size: 12px;
}

.actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

button {
  border: 0;
  border-radius: 6px;
  padding: 10px 12px;
  color: #fff;
  background: #18212f;
  cursor: pointer;
}

button.ghost {
  color: #18212f;
  background: #edf3fa;
}
</style>
