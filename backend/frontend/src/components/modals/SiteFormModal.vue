<template>
  <div v-if="visible" class="modal-backdrop" @click.self="$emit('close')">
    <form class="modal" @submit.prevent="submit">
      <button class="close" type="button" @click="$emit('close')">×</button>
      <h2>{{ draft.id ? "编辑网站" : "提交网站" }}</h2>
      <label>
        <span>网站名称</span>
        <input v-model.trim="draft.name" required />
      </label>
      <label>
        <span>网站链接</span>
        <input
          v-model.trim="draft.url"
          required
          placeholder="https://example.com"
        />
      </label>
      <label>
        <span>分类</span>
        <select v-model="draft.category_id">
          <option
            v-for="category in categories"
            :key="category.id"
            :value="category.id"
          >
            {{ category.name }}
          </option>
        </select>
      </label>
      <button class="primary" type="submit">保存</button>
    </form>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  site: {
    type: Object,
    default: () => ({}),
  },
  categories: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["save", "close"]);

const draft = reactive({
  id: null,
  name: "",
  url: "",
  category_id: "all",
});

watch(
  () => [props.visible, props.site, props.categories],
  () => {
    draft.id = props.site?.id || null;
    draft.name = props.site?.name || "";
    draft.url = props.site?.url || "";
    draft.category_id =
      props.site?.category_id || props.categories[0]?.id || "all";
  },
  { immediate: true, deep: true },
);

const submit = () => {
  emit("save", { ...draft });
};
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.45);
}

.modal {
  position: relative;
  display: grid;
  gap: 14px;
  width: min(460px, 100%);
  border-radius: 8px;
  padding: 28px;
  background: #fff;
}

h2 {
  margin: 0 0 6px;
}

label {
  display: grid;
  gap: 7px;
  color: #334155;
}

input,
select {
  border: 1px solid #d8e2ee;
  border-radius: 6px;
  padding: 11px 12px;
  font: inherit;
}

.primary {
  border: 0;
  border-radius: 6px;
  padding: 12px 16px;
  color: #fff;
  background: #18212f;
  cursor: pointer;
}

.close {
  position: absolute;
  top: 12px;
  right: 12px;
  border: 0;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
}
</style>
