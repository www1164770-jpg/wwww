<template>
  <div class="editor-container">
    <input v-model="form.title" placeholder="输入文章标题" class="title-input" />
    
    <div class="cover-uploader">
      <input type="file" @change="handleCoverUpload" accept="image/*" />
      <img v-if="form.cover_url" :src="form.cover_url" class="cover-preview" />
    </div>
    
    <QuillEditor v-model:content="form.content" contentType="html" theme="snow" style="height: 400px;" />
    
    <div class="actions">
      <button @click="submit('draft')">保存草稿</button>
      <button @click="submit('pending')" class="btn-primary">提交审核</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { QuillEditor } from '@vueup/vue-quill'
import '@vueup/vue-quill/dist/vue-quill.snow.css'
import axios from 'axios'

const form = ref({ title: '', cover_url: '', content: '', category: '', tags: [] })

const handleCoverUpload = async (e) => {
  // 这里写上传图片到服务器/OSS的代码，并将返回的 URL 赋给 form.value.cover_url
}

const submit = async (status) => {
  await axios.post('/api/articles', { ...form.value, status })
  alert(status === 'draft' ? '草稿已保存' : '已提交审核，请耐心等待')
}
</script>