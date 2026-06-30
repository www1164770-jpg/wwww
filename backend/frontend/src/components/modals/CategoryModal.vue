<template>
  <div v-if="visible" class="modal-backdrop" @click.self="$emit('close')">
    <form class="modal" @submit.prevent="submit">
      <button class="close" type="button" @click="$emit('close')">×</button>
      <h2>{{ draft.id ? "编辑分类" : "新建分类" }}</h2>
      <label>
        <span>分类名称</span>
        <input v-model.trim="draft.name" required />
      </label>
      <div class="actions">
        <button
          v-if="draft.id"
          class="danger"
          type="button"
          @click="$emit('delete', draft)"
        >
          删除
        </button>
        <button class="primary" type="submit">保存</button>
      </div>
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
  category: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(["save", "delete", "close"]);

const draft = reactive({ id: null, name: "" });

watch(
  () => [props.visible, props.category],
  () => {
    draft.id = props.category?.id || null;
    draft.name = props.category?.name || "";
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
  width: min(420px, 100%);
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
}

input {
  border: 1px solid #d8e2ee;
  border-radius: 6px;
  padding: 11px 12px;
  font: inherit;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

button {
  border: 0;
  border-radius: 6px;
  padding: 10px 14px;
  cursor: pointer;
}

.primary {
  color: #fff;
  background: #18212f;
}

.danger {
  color: #b91c1c;
  background: #fee2e2;
}

.close {
  position: absolute;
  top: 12px;
  right: 12px;
  background: transparent;
  font-size: 24px;
}
</style>
