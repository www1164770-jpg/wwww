// Run by agent-browser eval --stdin on the isolated Vite page only.
// Browser/runtime/HTTP are real; visibility and time are explicitly simulated.
(async()=>{
  const {observeRecommendationVisibility}=await import('/src/utils/recommendationVisibility.js');
  const auth=await import('/src/utils/auth.js');
  const saved={token:auth.getAccessToken(),user:auth.getStoredUserInfo()};
  const login=async account=>{const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({account,password:'Local-Integration-Only-2026!'})});if(!r.ok)throw Error('fixture login failed');return await r.json();};
  const a=await login('api_fixture'),b=await login('research_fixture');
  const oldSet=window.setTimeout,oldClear=window.clearTimeout,oldIO=window.IntersectionObserver;
  let now=0,seq=-1,callback,hidden=false;const timers=new Map(),requests=[],checks=[];
  const oldSend=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send=function(body){try{const x=JSON.parse(body);if(x.event_type==='impression'&&x.recommendation_batch_id?.startsWith('special-clock-'))requests.push({user:auth.getStoredUserInfo().id,at:now,batch:x.recommendation_batch_id,body:x});}catch{}return oldSend.call(this,body);};
  const batch='special-clock-'+Date.now();let stop;
  try {
    auth.saveAuthSession(a);
    window.setTimeout=(fn,ms,...args)=>{if(ms!==1000)return oldSet(fn,ms,...args);timers.set(--seq,{at:now+ms,fn});return seq;};
    window.clearTimeout=id=>timers.has(id)?timers.delete(id):oldClear(id);
    window.IntersectionObserver=class {constructor(fn){callback=fn;}observe(){}disconnect(){}};
    Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>hidden?'hidden':'visible'});
    const tick=ms=>{now+=ms;for(const [id,t] of [...timers])if(t.at<=now){timers.delete(id);t.fn();}};
    const visibility=value=>{hidden=value;document.dispatchEvent(new Event('visibilitychange'));};
    const ratio=n=>callback([{isIntersecting:n>0,intersectionRatio:n}]);
    const mount=()=>observeRecommendationVisibility(document.querySelector('.similar'),{id:91002,recommendation_batch_id:batch,event_version:'visible-v2',display_position:1});
    const check=(name,count)=>{if(requests.length!==count)throw Error(name);checks.push({name,at:now,requests:count});};
    stop=mount();ratio(.499);tick(1000);check('below half',0);
    ratio(.5);tick(999);visibility(true);tick(10000);check('999ms hidden and background excluded',0);
    const flush=async()=>{for(let i=0;i<30;i++)await Promise.resolve();};
    visibility(false);tick(999);check('foreground restarts',0);tick(1);await flush();check('1000ms emits',1);
    for(let i=0;i<10;i++){visibility(true);tick(10);visibility(false);tick(10);}tick(1000);check('rapid toggles no duplicate while inflight',1);
    stop();stop=mount();ratio(1);tick(999);auth.saveAuthSession(b);tick(1);check('old token timer cannot emit',1);
    stop();stop=mount();ratio(.5);tick(1000);await flush();check('new account independent event',2);
    stop();
    window.__specialVisibility={kind:'real Chromium + actual modules + real isolated HTTP; simulated clock/visibility/IntersectionObserver',batch,checks,requests};
  } finally {
    stop?.();window.setTimeout=oldSet;window.clearTimeout=oldClear;window.IntersectionObserver=oldIO;
    delete document.visibilityState;XMLHttpRequest.prototype.send=oldSend;
    // Keep account B active until its real request completes; no tokens in output.
  }
  return window.__specialVisibility;
})()
