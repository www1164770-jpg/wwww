import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ref,computed,reactive,watch,nextTick } from 'vue';
import { visibilityWindow } from '../src/utils/visibilityWindow.js';
import { recommendationPage } from '../src/utils/recommendationPages.js';
const source=readFileSync(new URL('../src/stores/recommendationPreferences.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace('export const useRecommendationPreferencesStore','const useRecommendationPreferencesStore');
const create=new Function('defineStore','ref','computed','watch','api','unwrapResponse','useUserStore',`${source};return useRecommendationPreferencesStore();`);
const user=reactive({isLoggedIn:false,userInfo:{id:1}});
let rejectSave,resolveSave,requests=0,items=[];
const api={get:async()=>({data:{enabled:true,items}}),post:()=>{requests++;return new Promise((resolve,reject)=>{resolveSave=resolve;rejectSave=reject;});}};
const store=create((_,setup)=>setup,ref,computed,watch,api,r=>r.data,()=>user);
assert.equal(await store.change({id:1},'later'),false);assert.equal(requests,0);
user.isLoggedIn=true;await nextTick();await nextTick();assert.equal(store.enabled.value,true);
const site={id:1,name:'fixture',feedback_enabled:true};
let pending=store.change(site,'irrelevant');assert.equal(store.excluded(site),true);
rejectSave({response:{status:503,data:{message:'反馈未保存'}}});assert.equal(await pending,false);assert.equal(Boolean(store.excluded(site)),false);assert.equal(store.error.value,'反馈未保存');
pending=store.change(site,'later');resolveSave({data:{website_id:1,revision:1,reason:'later',expires_at:'2026-10-26T00:00:00Z'}});assert.equal(await pending,true);assert.equal(store.undo.value.reason,null);
pending=store.change(site,null);resolveSave({data:{website_id:1,revision:2,reason:null,expires_at:null}});assert.equal(await pending,true);assert.equal(Boolean(store.excluded(site)),false);
pending=store.change(site,'known');user.userInfo={id:2};await nextTick();await nextTick();resolveSave({data:{website_id:1,revision:3,reason:'known'}});assert.equal(await pending,false);assert.deepEqual(store.rows.value,{});assert.equal(store.undo.value,null);
pending=store.change(site,'irrelevant');user.isLoggedIn=false;await nextTick();rejectSave({response:{status:503}});await pending;assert.deepEqual(store.rows.value,{});assert.equal(store.error.value,'');
// Account-scoped out-of-order list responses are also ignored.
const reads=[];api.get=()=>new Promise(resolve=>reads.push(resolve));user.isLoggedIn=true;await nextTick();user.userInfo={id:3};await nextTick();
reads[1]({data:{enabled:true,items:[{website_id:2,reason:'known',revision:1}]}});await nextTick();reads[0]({data:{enabled:true,items:[{website_id:1,reason:'irrelevant',revision:9}]}});await nextTick();
assert.equal(store.rows.value[1],undefined);assert.equal(store.rows.value[2].reason,'known');
store.rows.value={1:{website_id:1,reason:'later',expires_at:new Date(Date.now()+10).toISOString()}};store.now.value=Date.now();const previous=store.changed.value;
await new Promise(resolve=>setTimeout(resolve,15));store.tick();assert.equal(store.changed.value,previous+1);assert.equal(Boolean(store.excluded(site)),false);
console.log('PASS preference store: login, optimistic removal, failure rollback, undo, account/logout races, out-of-order lists, expiry');

let clock=0,serial=0,emitted=0,visible=true;const timers=new Map();
const gate=visibilityWindow({emit:()=>emitted++,visible:()=>visible,setTimer:(fn,delay)=>{timers.set(++serial,{fn,at:clock+delay});return serial;},clearTimer:id=>timers.delete(id)});
function advance(ms){clock+=ms;for(const [id,job] of [...timers])if(job.at<=clock){timers.delete(id);job.fn();}}
gate.update(.49);advance(2000);assert.equal(emitted,0);
gate.update(.5);advance(999);assert.equal(emitted,0);gate.update(.2);advance(2);assert.equal(emitted,0);
gate.update(.8);advance(500);visible=false;gate.update();advance(1000);assert.equal(emitted,0);
visible=true;gate.update();advance(999);assert.equal(emitted,0);advance(1);assert.equal(emitted,1);
gate.update(1);gate.stop();advance(2000);assert.equal(emitted,1);
console.log('PASS visibility: threshold, continuous duration, scroll reset, hidden-tab reset, unmount cancellation');
for(const size of [1,6,16]){
  const pool=Array.from({length:35},(_,i)=>({id:i+1}));const pages=[];
  for(let page=0;page<Math.ceil(pool.length/size);page++)pages.push(...recommendationPage(pool,page,size));
  assert.deepEqual(pages,pool);assert.equal(new Set(pages.map(x=>x.id)).size,35);
  assert.deepEqual(recommendationPage(pool,Math.ceil(pool.length/size),size),[]);
}
console.log('PASS pagination: 35 resources at sizes 1/6/16, exact coverage, no overlap or wrap fillers');
