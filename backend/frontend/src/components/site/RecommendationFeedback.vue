<template>
  <details v-if="site.feedback_enabled && store.enabled" name="recommendation-feedback" class="recommendation-feedback" @click.stop @keydown.stop @keydown.esc.prevent="$event.currentTarget.open = false">
    <summary aria-label="推荐反馈" title="推荐反馈">⋯</summary>
    <div class="recommendation-feedback__menu" role="group" aria-label="调整推荐">
      <button v-for="option in options" :key="option[0]" type="button" :disabled="store.pending[site.id]" @click.stop="submit(option[0], $event)">{{ option[1] }}</button>
    </div>
  </details>
</template>
<script setup>
import { useRecommendationPreferencesStore } from '../../stores/recommendationPreferences';
const props=defineProps({site:{type:Object,required:true}});
const store=useRecommendationPreferencesStore();
const options=[['irrelevant','不相关'],['known','已经知道'],['later','暂时不需要']];
async function submit(reason,event) { const menu=event.currentTarget.closest('details');await store.change(props.site,reason);if(menu)menu.open=false; }
</script>
<style scoped>
.recommendation-feedback{position:absolute;right:2.5rem;top:.5rem;z-index:5;color:var(--color-text-secondary,#666)}
summary{cursor:pointer;list-style:none;padding:0 .5rem;font-size:1.3rem}summary::-webkit-details-marker{display:none}
.recommendation-feedback__menu{position:absolute;right:0;top:100%;min-width:8rem;display:grid;background:#fff;border:1px solid var(--color-border,#ddd);border-radius:8px;box-shadow:0 4px 12px #0001;padding:4px}
button{border:0;background:white;text-align:left;padding:8px;cursor:pointer;color:inherit}button:hover{background:#f5f5f5}
</style>
