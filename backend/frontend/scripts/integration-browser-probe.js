// Explicit TEST instrumentation, injected only into the isolated browser tab.
// Keep real route bodies/auth and AbortSignal behavior. Extend XHR timeout so a
// file-controlled barrier (rather than random sleeps) determines delivery order.
(() => {
  if (window.__integrationProbe) return;
  const events=[];
  window.__integrationProbe={events,started:Date.now()};
  window.__integrationSnapshot=()=>{
    const stores=document.querySelector('#app').__vue_app__.config.globalProperties.$pinia._s;
    const favorites=stores.get('favorites'),preferences=stores.get('recommendationPreferences');
    return {
      user:stores.get('user')?.userInfo?.id,
      cards:[...document.querySelectorAll('[data-testid="career-site-batch"] article')].map(x=>x.innerText),
      heading:[...document.querySelectorAll('h2')].map(x=>x.textContent).find(x=>x.includes('的网站工具')),
      favorites:favorites?.items.map(x=>x.siteId||x.id),favoriteUser:favorites?.activeUserId,
      preferences:JSON.parse(JSON.stringify(preferences?.rows||{})),pending:JSON.parse(JSON.stringify(preferences?.pending||{})),
      undo:preferences?.undo||null,error:preferences?.error||'',
    };
  };
  const open=XMLHttpRequest.prototype.open,send=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open=function(method,url,...rest){
    this.__integrationRequest={method,path:String(url),started:Date.now()};
    return open.call(this,method,url,...rest);
  };
  XMLHttpRequest.prototype.send=function(...args){
    const entry=this.__integrationRequest;
    if(entry?.path.includes('/api/')){
      this.timeout=300000;
      this.addEventListener('loadend',()=>{
        let data={};try{data=JSON.parse(this.responseText)?.data||{};}catch{}
        events.push({...entry,ended:Date.now(),status:this.status,ids:(data.websites||data.items||[]).map(x=>x.id??x.website_id),selected_career:data.selected_career,enabled:data.enabled});
      },{once:true});
    }
    return send.apply(this,args);
  };
})();
