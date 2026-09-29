import assert from 'node:assert/strict';
import {readFileSync, writeFileSync} from 'node:fs';
import {visibilityWindow} from '../src/utils/visibilityWindow.js';
let now=0, seq=0, account=1, hidden=false, io, listener;
const timers=new Map(), storage=new Map(), events=[], checks=[];
const setTimer=(fn,ms)=>{timers.set(++seq,{at:now+ms,fn});return seq;};
const clearTimer=id=>timers.delete(id);
const tick=ms=>{const end=now+ms; for(;;){const next=[...timers].filter(([,v])=>v.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];if(!next)break;now=next[1].at;timers.delete(next[0]);next[1].fn();}now=end;};
const document={get visibilityState(){return hidden?'hidden':'visible';},addEventListener:(name,fn)=>listener=fn,removeEventListener:()=>listener=null};
class IntersectionObserver {constructor(fn){io=fn;}observe(){}disconnect(){}}
const source=readFileSync(new URL('../src/utils/recommendationVisibility.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace(/export /g,'');
const observe=new Function('getStoredUserInfo','getAccessToken','isValidAuthToken','visibilityWindow','trackVisibleImpression','IntersectionObserver','document','sessionStorage',source+';return observeRecommendationVisibility;')(
  ()=>({id:account}),()=>`token-${account}`,()=>true,
  args=>visibilityWindow({...args,setTimer,clearTimer}),
  async site=>{events.push({account,at:now,batch:site.recommendation_batch_id});return {};},
  IntersectionObserver,document,{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)});
const ratio=n=>io([{isIntersecting:n>0,intersectionRatio:n}]);
const visibility=value=>{hidden=value;listener?.();};
const check=(name,count)=>{assert.equal(events.length,count,name);checks.push({name,events:count,at:now});};
let stop=observe({}, {id:11,recommendation_batch_id:'boundary'});
ratio(.499);tick(2000);check('49.9% never qualifies',0);
ratio(.5);tick(999);visibility(true);check('hidden at 999ms cancels',0);
tick(10000);check('background time excluded',0);
visibility(false);tick(999);check('foreground restarts full 1000ms',0);
tick(1);await Promise.resolve();check('exactly 1000ms at 50%',1);
for(let i=0;i<10;i++){visibility(true);tick(20);visibility(false);tick(30);}
tick(1000);await Promise.resolve();check('rapid toggles no duplicate',1);
stop();stop=observe({}, {id:11,recommendation_batch_id:'switch'});ratio(1);tick(999);account=2;tick(1);check('old account timer cannot emit for new account',1);
stop();stop=observe({}, {id:11,recommendation_batch_id:'boundary'});ratio(.5);tick(1000);await Promise.resolve();check('new account independent dedupe',2);
assert.equal(events[1].account,2);
stop();account=1;stop=observe({}, {id:11,recommendation_batch_id:'boundary'});ratio(1);tick(1000);await Promise.resolve();check('returning account retains session dedupe',2);
stop();assert.equal(timers.size,0);check('unmount cancels timers',2);
const report={kind:'simulated-clock, real visibilityWindow and observer module with injected DOM/auth/transport',checks,events};
writeFileSync(new URL('../../../artifacts/local-integration/visibility-clock.json',import.meta.url),JSON.stringify(report,null,2));
console.log(JSON.stringify(report));
