"""Targeted regression for the missing card reveal and clipped pricing reason."""
import json
from verify_special_browser import ab,js,snap,OUT,check
ab('record','start',str(OUT/'similar-visual-final.webm'),'--fps','5')
results=[]
for width,height,name in [(1440,1000,'desktop'),(390,844,'narrow')]:
    ab('set','viewport',str(width),str(height))
    for index in range(2):
        state=js(f"""(async()=>{{const e=document.querySelectorAll('.similar .site-card-reveal')[{index}];e.scrollIntoView({{block:'center',behavior:'instant'}});await new Promise((resolve,reject)=>{{const deadline=performance.now()+5000;const poll=()=>{{if(Number(getComputedStyle(e).opacity)>.999)resolve();else if(performance.now()>deadline)reject(Error('card remains transparent'));else requestAnimationFrame(poll)}};poll()}});const r=e.getBoundingClientRect();const reason=e.querySelector('.site-card__reason-text');const controls=[...e.querySelectorAll('button,a')].map(b=>{{const t=b.getBoundingClientRect();return {{text:b.textContent.trim()||b.getAttribute('aria-label'),clear:b.contains(document.elementFromPoint(t.x+t.width/2,t.y+t.height/2))}}}});return {{width:innerWidth,opacity:getComputedStyle(e).opacity,overflow:document.documentElement.scrollWidth>innerWidth,reason:reason.textContent,unclipped:reason.scrollHeight<=reason.clientHeight+1,controls,left:r.left,right:r.right,top:r.top,bottom:r.bottom}}}})()""")
        check(f'{name} card {index} visible, reason complete, controls unobscured',float(state['opacity'])>.999 and not state['overflow'] and state['unclipped'] and all(x['clear'] for x in state['controls']) and state['left']>=0 and state['right']<=width)
        results.append(state)
        ab('screenshot',str(OUT/f'similar-{name}-final-{index}.png'))
(OUT/'similar-visual-final.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
try:ab('record','stop')
except RuntimeError as exc:(OUT/'similar-visual-recording-limitation.txt').write_text(str(exc),encoding='utf-8')
print('PASS 4 visible card frames: opacity, complete reason, horizontal bounds, button hit tests')
