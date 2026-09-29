<template>
  <section v-if="store.enabled || store.error" :class="compact ? 'feedback-notice' : 'editor-card personalization-section'" aria-label="推荐偏好" aria-live="polite">
    <template v-if="!compact">
      <h2>推荐偏好</h2><p>只影响主动推荐，不影响搜索、详情或收藏。不相关可随时恢复；已知资源在相近结果中后置，暂时不需要到期恢复。</p>
      <p v-if="!activeRows.length">尚无有效反馈。</p>
      <div v-for="row in activeRows" :key="row.website_id"><span>{{ row.name || `资源 ${row.website_id}` }} · {{ labels[row.reason] }} {{ row.expires_at ? `（至 ${new Date(row.expires_at).toLocaleDateString()}）` : '' }}</span> <button type="button" :disabled="store.pending[row.website_id]" @click="store.change({id:row.website_id,name:row.name},null)">恢复推荐</button></div>
    </template>
    <p v-if="store.error" role="alert">{{ store.error }} <button type="button" @click="store.load()">重试</button></p>
    <p v-if="store.undo">已调整此资源的推荐。<button type="button" :disabled="store.pending[store.undo.site.id]" @click="store.undoLast()">撤销</button> <RouterLink to="/personalization">管理推荐偏好</RouterLink></p>
  </section>
</template>
<script setup>
import { computed,onMounted,onBeforeUnmount } from 'vue';
import { useRecommendationPreferencesStore } from '../../stores/recommendationPreferences';
defineProps({compact:{type:Boolean,default:false}});
const store=useRecommendationPreferencesStore(),labels={irrelevant:'不相关',known:'已经知道',later:'暂时不需要'};
const activeRows=computed(()=>Object.values(store.rows).filter(row=>store.active(row)));
let timer;
onMounted(()=>{timer=setInterval(()=>store.tick(),1000);});
onBeforeUnmount(()=>clearInterval(timer));
</script>
<style scoped>
.feedback-notice:empty{display:none}.feedback-notice{position:fixed;bottom:1rem;right:1rem;z-index:1100;background:#fff;border:1px solid var(--color-border,#ddd);border-radius:8px;max-width:min(28rem,calc(100vw - 2rem));padding:0 12px;box-shadow:0 4px 14px #0001}
button{cursor:pointer;background:white;border:1px solid var(--color-border,#ddd);border-radius:6px;padding:4px 8px;color:inherit}
</style>
