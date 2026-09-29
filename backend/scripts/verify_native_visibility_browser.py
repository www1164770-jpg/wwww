import json
from verify_special_browser import ab,js,OUT,ROOT,check
ab('eval','--stdin',script=(ROOT/'backend/frontend/scripts/integration-visibility-native.js').read_text(encoding='utf-8'))
ab('tab','new','about:blank')
# A specified >1000ms hidden interval, not a random wait to catch a race.
ab('eval','--stdin',script='new Promise(resolve=>setTimeout(()=>resolve(true),1500))')
ab('tab','t1')
ab('eval','--stdin',script="new Promise((resolve,reject)=>{const deadline=performance.now()+5000;const poll=()=>{if(window.__nativeVisibility.events.some(e=>e.type==='response'))resolve(true);else if(performance.now()>deadline)reject(Error('response timeout'));else setTimeout(poll,20)};poll()})")
state=js('window.__nativeVisibility')
hidden=next(e for e in state['events'] if e['type']=='visibilitychange' and e['visibility']=='hidden')
visible=next(e for e in state['events'] if e['type']=='visibilitychange' and e['visibility']=='visible')
armed=next(e for e in state['events'] if e['type']=='armed')
check('native hidden before threshold',0<=hidden['ms']-armed['ms']<1000)
check('native background > threshold',visible['ms']-hidden['ms']>=1000)
check('only one native event, full foreground restart',len(state['requests'])==1 and state['requests'][0]['ms']-visible['ms']>=990)
ab('eval','--stdin',script='window.__stopNative()')
(OUT/'visibility-native.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(state))
