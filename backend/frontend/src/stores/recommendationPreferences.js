import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';
import { api, unwrapResponse } from '../utils/api';
import { useUserStore } from './user';

export const useRecommendationPreferencesStore = defineStore('recommendationPreferences', () => {
  const user=useUserStore();
  const identity=computed(()=>user.isLoggedIn ? String(user.userInfo?.id || user.userInfo?.username || '') : '');
  const enabled=ref(false), rows=ref({}), pending=ref({}), error=ref(''), undo=ref(null), changed=ref(0);
  const now=ref(Date.now());
  let epoch=0, read=0;
  const active=row=>row?.reason && (!row.expires_at || Date.parse(row.expires_at)>now.value);
  // Callers opt in by surface, not by possibly stale resource metadata.
  const excluded=site=>enabled.value && active(rows.value[site.id]) && ['irrelevant','later'].includes(rows.value[site.id].reason);
  function tick() {
    const before=Object.values(rows.value).filter(active).length;
    now.value=Date.now();
    if (before!==Object.values(rows.value).filter(active).length) changed.value++;
  }
  async function load() {
    const account=identity.value, generation=epoch, sequence=++read;
    if (!account) return;
    try {
      const data=unwrapResponse(await api.get('/recommendation/preferences'));
      if (account!==identity.value || generation!==epoch || sequence!==read) return;
      const previous=JSON.stringify([enabled.value,rows.value]);
      enabled.value=Boolean(data.enabled);rows.value=Object.fromEntries((data.items||[]).map(row=>[row.website_id,row]));error.value='';now.value=Date.now();
      if(previous!==JSON.stringify([enabled.value,rows.value]))changed.value++;
    } catch {
      if (account===identity.value && generation===epoch && sequence===read) error.value='推荐偏好读取失败，请重试。';
    }
  }
  watch(identity,()=>{epoch++;read++;enabled.value=false;rows.value={};pending.value={};undo.value=null;error.value='';void load();},{immediate:true});
  async function change(site,reason,expectedRevision=null) {
    const account=identity.value,generation=epoch,id=site.id;
    if (!account || !enabled.value || pending.value[id]) return false;
    if(expectedRevision!==null && expectedRevision!==(rows.value[id]?.revision||0)) {error.value='偏好已变化，请在设置页核对后恢复。';return false;}
    read++;const previous=rows.value[id];pending.value={...pending.value,[id]:true};error.value='';
    rows.value={...rows.value,[id]:{...previous,website_id:id,name:site.name,reason,expires_at:null}};
    try {
      const data=unwrapResponse(await api.post('/recommendation/preferences',{
        website_id:Number(id),reason,expected_revision:expectedRevision ?? previous?.revision ?? 0,request_id:crypto.randomUUID(),
        recommendation_batch_id:site.recommendation_batch_id||'',algorithm_version:site.algorithm_version||'phase1-v1',rerank_version:site.rerank_version||'baseline',
      }));
      if (account!==identity.value || generation!==epoch) return false;
      if(data.revision<(rows.value[id]?.revision||0)) {error.value='偏好已更新，已保留最新状态。';return false;}
      rows.value={...rows.value,[id]:{...data,name:site.name}};
      undo.value=reason?{site,reason:null,revision:data.revision}:null;changed.value++;return true;
    } catch (failure) {
      if (account!==identity.value || generation!==epoch) return false;
      rows.value={...rows.value,[id]:previous};error.value=failure?.response?.data?.message||'无法确认是否保存，已恢复显示，请刷新偏好核对。';
      // Refresh after an ambiguous timeout or revision conflict; never overwrite a newer account.
      if (failure?.response?.status===409 || !failure?.response) {
        await load();
        if(account===identity.value && generation===epoch) error.value='已核对当前偏好，请在设置页确认或重试。';
      }
      return false;
    } finally {
      if (account===identity.value && generation===epoch) { const copy={...pending.value};delete copy[id];pending.value=copy; }
    }
  }
  const undoLast=()=>undo.value ? change(undo.value.site,null,undo.value.revision) : false;
  return {enabled,rows,pending,error,undo,changed,now,active,excluded,load,change,tick,undoLast};
});
