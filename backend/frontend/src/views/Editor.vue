<template>
  <div class="editor-container">
    <input
      v-model="form.title"
      placeholder="输入文章标题"
      class="title-input"
    />

    <div class="cover-uploader">
      <input type="file" @change="handleCoverUpload" accept="image/*" />
      <img v-if="form.cover_url" :src="form.cover_url" class="cover-preview" />
    </div>

    <QuillEditor
      v-model:content="form.content"
      contentType="html"
      theme="snow"
      style="height: 400px"
    />

    <div class="actions">
      <button @click="submit('draft')">保存草稿</button>
      <button @click="submit('pending')" class="btn-primary">提交审核</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { QuillEditor } from "@vueup/vue-quill";
import "@vueup/vue-quill/dist/vue-quill.snow.css";
import axios from "axios";

const form = ref({
  title: "",
  cover_url: "",
  content: "",
  category: "",
  tags: [],
});

const handleCoverUpload = async (e) => {
  // 这里写上传图片到服务器/OSS的代码，并将返回的 URL 赋给 form.value.cover_url
};

const submit = async (status) => {
  await axios.post("/api/articles", { ...form.value, status });
  alert(status === "draft" ? "草稿已保存" : "已提交审核，请耐心等待");
};
</script>

<style scoped>
.editor-container {
  min-height: 100vh;
  max-width: 980px;
  margin: 0 auto;
  padding: clamp(24px, 5vw, 56px);
  color: var(--mono-text);
  animation: mono-rise-in 0.64s var(--mono-ease);
}

.title-input {
  width: 100%;
  min-height: 68px;
  margin-bottom: 18px;
  padding: 0 22px;
  color: var(--mono-text);
  background: var(--mono-surface) !important;
  border: 1px solid var(--mono-border);
  border-radius: var(--mono-radius-lg);
  box-shadow: var(--mono-shadow-sm);
  font-size: clamp(24px, 4vw, 38px);
  font-weight: 800;
  letter-spacing: -0.06em;
  outline: none;
}

.cover-uploader {
  margin-bottom: 18px;
  padding: 22px;
  color: var(--mono-muted);
  background: var(--mono-surface);
  border: 1px dashed var(--mono-border-strong);
  border-radius: var(--mono-radius-lg);
  box-shadow: var(--mono-shadow-sm);
}

.cover-uploader input {
  width: 100%;
}

.cover-preview {
  display: block;
  width: 100%;
  max-height: 260px;
  margin-top: 16px;
  object-fit: cover;
  border-radius: var(--mono-radius-md);
  filter: grayscale(1);
}

:deep(.ql-toolbar),
:deep(.ql-container) {
  background: rgba(255, 255, 255, 0.78);
  border-color: var(--mono-border) !important;
}

:deep(.ql-toolbar) {
  border-radius: var(--mono-radius-lg) var(--mono-radius-lg) 0 0;
}

:deep(.ql-container) {
  border-radius: 0 0 var(--mono-radius-lg) var(--mono-radius-lg);
  box-shadow: var(--mono-shadow-sm);
}

:deep(.ql-editor) {
  color: var(--mono-text);
  font-size: 16px;
  line-height: 1.8;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.actions button {
  padding: 0 22px;
  color: var(--mono-text);
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid var(--mono-border);
  border-radius: 999px;
  transition:
    transform var(--mono-base) var(--mono-ease),
    background var(--mono-base) var(--mono-ease);
}

.actions button:hover {
  transform: translateY(-2px);
  background: #ffffff;
}

@media (max-width: 680px) {
  .editor-container {
    padding: 18px;
  }

  .actions {
    flex-direction: column;
  }
}
</style>
