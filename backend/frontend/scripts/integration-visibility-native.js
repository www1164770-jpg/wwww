(async()=>{
  const {observeRecommendationVisibility}=await import('/src/utils/recommendationVisibility.js');
  const element=document.querySelector('.similar .site-card');
  element.scrollIntoView({block:'center',behavior:'instant'});
  const state={kind:'native Chromium visibility, IntersectionObserver and wall clock; real isolated HTTP',batch:'special-native-'+Date.now(),events:[],requests:[]};
  window.__nativeVisibility=state;
  const start=performance.now();
  const mark=(type,extra={})=>state.events.push({type,ms:performance.now()-start,visibility:document.visibilityState,...extra});
  const send=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send=function(body){try{const data=JSON.parse(body);if(data.recommendation_batch_id===state.batch){state.requests.push({ms:performance.now()-start,body:data});this.addEventListener('loadend',()=>mark('response',{status:this.status}));}}catch{}return send.call(this,body);};
  const listener=()=>mark('visibilitychange');document.addEventListener('visibilitychange',listener);
  const stop=observeRecommendationVisibility(element,{id:91002,recommendation_batch_id:state.batch,event_version:'visible-v2',display_position:1});
  await new Promise(resolve=>{const observer=new IntersectionObserver(entries=>{if(entries[0].intersectionRatio>=.5){mark('armed',{ratio:entries[0].intersectionRatio});observer.disconnect();resolve();}},{threshold:[.5]});observer.observe(element);});
  window.__stopNative=()=>{stop();document.removeEventListener('visibilitychange',listener);XMLHttpRequest.prototype.send=send;};
  return {batch:state.batch,armed:state.events};
})()
