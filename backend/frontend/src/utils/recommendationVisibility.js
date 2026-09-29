import { getAccessToken,getStoredUserInfo,isValidAuthToken } from './auth';
import { trackVisibleImpression } from './behaviorTracker';
import { visibilityWindow } from './visibilityWindow';
const inflight=new Set();
const memory=new Set();
export function observeRecommendationVisibility(element,site) {
  if(typeof IntersectionObserver==='undefined' || !site.recommendation_batch_id)return ()=>{};
  const account=getStoredUserInfo();const token=getAccessToken();
  const key=JSON.stringify([account.id||account.username,site.recommendation_batch_id,site.id,'visible-v2',site.rerank_version||'baseline']);
  const storageKey='zhihangyu:visible-v2:'+key;
  function seen(){try{return sessionStorage.getItem(storageKey)==='1';}catch{return memory.has(key);}}
  let stopped=false;
  const gate=visibilityWindow({visible:()=>!stopped && document.visibilityState==='visible' && token===getAccessToken() && isValidAuthToken(token),emit:async()=>{
    if(seen() || inflight.has(key))return;
    inflight.add(key);
    try {
      const result=await trackVisibleImpression(site);
      if(!result.error && !result.anonymous && token===getAccessToken()) {memory.add(key);try{sessionStorage.setItem(storageKey,'1');}catch{ /* no persistent storage */ }}
    } finally {inflight.delete(key);}
  }});
  const observer=new IntersectionObserver(entries=>{for(const entry of entries)gate.update(entry.isIntersecting?entry.intersectionRatio:0);},{threshold:[0,.5,1]});
  const visibility=()=>gate.update();
  document.addEventListener('visibilitychange',visibility);observer.observe(element);
  return ()=>{stopped=true;gate.stop();observer.disconnect();document.removeEventListener('visibilitychange',visibility);};
}
