// Read-only geometry sampling of actual browser frames; no style/animation changes.
(() => {
  window.__visualFrames=[];
  window.__visualStop=false;
  const started=performance.now();let last=0;
  const frame=now=>{
    if(window.__visualStop||now-started>15000)return;
    if(now-last>=50){
      last=now;
      const menu=document.querySelector('details[open] .recommendation-feedback__menu');
      const rect=menu?.getBoundingClientRect();
      const card=document.querySelector('[data-testid="career-site-batch"] article')?.getBoundingClientRect();
      const buttons=menu?[...menu.querySelectorAll('button')]:[];
      window.__visualFrames.push({ms:Math.round(now-started),overflow:document.documentElement.scrollWidth>innerWidth,
        card:card?{x:card.x,y:card.y,w:card.width,h:card.height}:null,
        menu:rect?{x:rect.x,y:rect.y,w:rect.width,h:rect.height,inside:rect.left>=0&&rect.right<=innerWidth&&rect.top>=0&&rect.bottom<=innerHeight,
          buttonsAccessible:buttons.every(b=>{const r=b.getBoundingClientRect();return b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));})}:null,
        animationCount:document.getAnimations().length});
    }
    requestAnimationFrame(frame);
  };requestAnimationFrame(frame);
})();
