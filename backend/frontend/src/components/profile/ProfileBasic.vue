<template>
  <section class="panel">
    <div class="heading">
      <p>基础资料</p>
      <h1>编辑公开信息</h1>
    </div>

    <form class="form-card" @submit.prevent="$emit('save')">
      <label>
        <span>昵称</span>
        <input
          :value="form.username"
          @input="$emit('update:field', 'username', $event.target.value)"
        />
      </label>
      <label>
        <span>性别</span>
        <select
          :value="form.gender"
          @change="$emit('update:field', 'gender', $event.target.value)"
        >
          <option value="保密">保密</option>
          <option value="男">男</option>
          <option value="女">女</option>
        </select>
      </label>
      <label>
        <span>生日</span>
        <input
          :value="form.birthday"
          type="date"
          @input="$emit('update:field', 'birthday', $event.target.value)"
        />
      </label>
      <label>
        <span>个人简介</span>
        <textarea
          :value="form.bio"
          rows="4"
          @input="$emit('update:field', 'bio', $event.target.value)"
        ></textarea>
      </label>
      <button type="submit">保存基础资料</button>
    </form>
  </section>
</template>

<script setup>
defineProps({
  form: {
    type: Object,
    required: true,
  },
});

defineEmits(["update:field", "save"]);
</script>

<style scoped>
.panel {
  display: grid;
  gap: 20px;
}

.heading p,
.heading h1 {
  margin: 0;
}

.heading p {
  color: #1769aa;
  font-weight: 700;
}

.form-card {
  display: grid;
  gap: 14px;
  max-width: 680px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  padding: 22px;
  background: #fff;
}

label {
  display: grid;
  gap: 7px;
}

input,
select,
textarea {
  border: 1px solid #d8e2ee;
  border-radius: 6px;
  padding: 11px 12px;
  font: inherit;
}

button {
  justify-self: start;
  border: 0;
  border-radius: 6px;
  padding: 11px 16px;
  color: #fff;
  background: #18212f;
  cursor: pointer;
}
</style>
