<template>
  <form class="questionnaire-form" @submit.prevent="$emit('submit', form)">
    <label>
      Occupation
      <select v-model="form.occupation" required>
        <option disabled value="">Select occupation</option>
        <option v-for="item in occupations" :key="item" :value="item">
          {{ item }}
        </option>
      </select>
    </label>
    <label>
      Skill level
      <select v-model="form.skill_level" required>
        <option disabled value="">Select level</option>
        <option v-for="item in skillLevels" :key="item" :value="item">
          {{ item }}
        </option>
      </select>
    </label>
    <fieldset>
      <legend>Purpose</legend>
      <label v-for="item in purposes" :key="item">
        <input v-model="form.purposes" type="checkbox" :value="item" />
        {{ item }}
      </label>
    </fieldset>
    <fieldset>
      <legend>Interests</legend>
      <label v-for="item in interests" :key="item">
        <input v-model="form.interests" type="checkbox" :value="item" />
        {{ item }}
      </label>
    </fieldset>
    <fieldset>
      <legend>Preferences</legend>
      <label v-for="item in preferences" :key="item">
        <input v-model="form.preferences" type="checkbox" :value="item" />
        {{ item }}
      </label>
    </fieldset>
    <button type="submit">Save profile</button>
  </form>
</template>

<script setup>
import { reactive } from "vue";

defineProps({
  occupations: { type: Array, default: () => [] },
  purposes: { type: Array, default: () => [] },
  interests: { type: Array, default: () => [] },
  skillLevels: { type: Array, default: () => [] },
  preferences: { type: Array, default: () => [] },
});
defineEmits(["submit"]);

const form = reactive({
  occupation: "",
  skill_level: "",
  purposes: [],
  interests: [],
  preferences: [],
});
</script>

<style scoped>
.questionnaire-form {
  display: grid;
  gap: 18px;
}
label,
fieldset {
  display: grid;
  gap: 8px;
}
fieldset {
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
}
legend {
  color: #111827;
  font-weight: 800;
}
select {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 11px;
}
button {
  border: 0;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  padding: 13px;
  font-weight: 800;
}
</style>
