<template>
  <div class="dmca-container block-shadow">
    <h2>版权申诉与 DMCA 投诉</h2>
    <p class="notice">
      如果您认为本站上的内容侵犯了您的版权，请填写下方表单，我们将依法核实并下架侵权内容。
    </p>

    <form @submit.prevent="submitDMCA" class="dmca-form">
      <div class="form-group">
        <label>投诉方名称 / 版权方</label>
        <input type="text" v-model="form.name" required class="auth-input" />
      </div>
      <div class="form-group">
        <label>联系邮箱 (用于接收处理进度)</label>
        <input type="email" v-model="form.email" required class="auth-input" />
      </div>
      <div class="form-group">
        <label>侵权内容链接 (URL)</label>
        <input type="url" v-model="form.url" required class="auth-input" />
      </div>
      <div class="form-group">
        <label>侵权描述与权属证明</label>
        <textarea
          v-model="form.desc"
          required
          class="auth-input"
          rows="5"
        ></textarea>
      </div>
      <button type="submit" class="btn-primary" :disabled="isSubmitting">
        {{ isSubmitting ? "提交中..." : "提交版权申诉" }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import axios from "axios";

const form = ref({ name: "", email: "", url: "", desc: "" });
const isSubmitting = ref(false);

const submitDMCA = async () => {
  isSubmitting.value = true;
  try {
    const res = await axios.post("/api/dmca", form.value);
    alert(res.data.msg);
    form.value = { name: "", email: "", url: "", desc: "" };
  } catch (error) {
    alert("提交失败，请重试");
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.dmca-container {
  max-width: 800px;
  margin: 40px auto;
  padding: 40px;
  background: white;
  border-radius: 16px;
}
.notice {
  color: #eab308;
  background: #fef9c3;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}
.dmca-form .form-group {
  margin-bottom: 20px;
}
.dmca-form label {
  display: block;
  margin-bottom: 8px;
  font-weight: bold;
  color: #334155;
}
</style>
