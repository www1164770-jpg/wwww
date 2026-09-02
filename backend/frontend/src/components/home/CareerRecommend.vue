<template>
  <section class="home-section career-section">
    <div class="section-heading">
      <p>职业推荐</p>
      <h2>选择你的职业，快速找到适合的工具组合。</h2>
    </div>

    <div class="career-grid">
      <button
        v-for="career in recommendations"
        :key="career.careerCode || career.career_code || career.code"
        type="button"
        class="career-card"
        :class="{
          active:
            activeCareerCode ===
            (career.careerCode || career.career_code || career.code),
        }"
        @click="selectCareer(career)"
      >
        <span class="career-icon">{{ career.label || career.careerName }}</span>
        <strong>{{ career.label || career.careerName }}</strong>
        <small>{{ career.reason || career.reasons?.[0] }}</small>
        <span class="tag-row">
          <em
            v-for="keyword in career.interest_tags ||
            career.occupation_tags ||
            []"
            :key="keyword"
          >
            {{ keyword }}
          </em>
        </span>
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  recommendations: {
    type: Array,
    default: () => [],
  },
  activeCareerCode: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["select-career"]);

function selectCareer(career) {
  emit("select-career", career);
}
</script>

<style scoped>
.career-section {
  display: grid;
  gap: 28px;
  margin-top: 28px;
  border-radius: var(--radius-large);
  background: var(--app-page-bg);
  padding: 54px 34px 42px;
}

.career-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

.career-card {
  display: grid;
  gap: 14px;
  min-height: 238px;
  border: 1px solid var(--app-border);
  border-radius: var(--radius-card);
  padding: 22px;
  text-align: left;
  background: var(--app-card-bg);
  backdrop-filter: blur(var(--app-blur));
  box-shadow: var(--app-card-shadow);
  transition:
    border-color var(--transition),
    transform var(--transition),
    box-shadow var(--transition),
    background var(--transition);
}

.career-card:hover,
.career-card.active {
  border-color: #ff7058;
  background: var(--app-card-hover-bg);
  transform: translateY(-5px);
  box-shadow: var(--app-card-hover-shadow);
}

.career-card.active {
  box-shadow: var(--app-card-hover-shadow);
}

.career-icon {
  display: grid;
  width: 50px;
  height: 50px;
  place-items: center;
  border-radius: 18px;
  color: #ffffff;
  background: var(--color-primary);
  font-weight: 850;
}

.career-card strong {
  color: var(--color-heading);
  font-size: 18px;
}

.career-card small {
  color: var(--color-text);
  line-height: 1.65;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-row em {
  border-radius: var(--radius-pill);
  padding: 6px 10px;
  color: var(--color-primary-dark);
  background: rgba(255, 112, 88, 0.1);
  font-size: 12px;
  font-style: normal;
  font-weight: 750;
}

@media (max-width: 980px) {
  .career-section {
    padding-inline: 24px;
  }

  .career-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .career-section {
    padding-inline: 18px;
  }

  .career-grid {
    grid-template-columns: 1fr;
  }
}
</style>
