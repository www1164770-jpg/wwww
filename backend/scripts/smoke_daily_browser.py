"""Brief browser smoke of the running daily site, with private test credentials."""
import json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'artifacts/daily-activation'
backup=json.loads((out/'backup-manifest.json').read_text());account=json.loads((Path(backup['backup_directory'])/'smoke-account.json').read_text())
cli=Path(os.environ['TEMP'])/'zhihangyu-integration-tools/node_modules/agent-browser/bin/agent-browser-win32-x64.exe'
steps=[]
def ab(*args,script=None,private=False):
    r=subprocess.run([str(cli),'--session','dailysmoke',*args],input=script,text=True,encoding='utf-8',capture_output=True)
    steps.append({'command':[args[0],'private test credential input'] if private else list(args),'output':r.stdout,'error':r.stderr,'exit':r.returncode})
    (out/'browser-smoke.json').write_text(json.dumps(steps,ensure_ascii=False,indent=2),encoding='utf-8')
    assert r.returncode==0,r.stderr
    return r.stdout
ab('click','@e1')
ab('fill','@e10',account['username'],private=True)
ab('fill','@e11',account['password'],private=True)
ab('click','@e8');ab('wait','button[aria-label="打开用户菜单"]')
ab('set','viewport','1440','1000')
ab('wait','[data-testid="career-site-batch"]')
ab('scrollintoview','[data-testid="career-site-batch"]')
ab('snapshot','-i')
# Wait on an observable successful visible-v2 dedupe marker, not a random delay.
result=ab('eval','--stdin',script="new Promise((resolve,reject)=>{const deadline=performance.now()+10000;const poll=()=>{const keys=Object.keys(sessionStorage).filter(k=>k.startsWith('zhihangyu:visible-v2:'));if(keys.length)resolve({visibleImpressionKeys:keys.length});else if(performance.now()>deadline)reject(Error('no visible impression'));else setTimeout(poll,50)};poll()})")
ab('screenshot',str(out/'daily-home.png'))
ab('open','http://127.0.0.1:5173/search?q=GitHub');ab('wait','.site-card');ab('snapshot','-i')
ab('screenshot',str(out/'daily-search.png'))
sid=json.loads((out/'smoke-http.json').read_text(encoding='utf-8'))['site_id']
ab('open',f'http://127.0.0.1:5173/site/{sid}');ab('wait','.similar');ab('snapshot','-i')
ab('eval','--stdin',script="document.querySelector('.similar .site-card').scrollIntoView({block:'center',behavior:'instant'});new Promise((resolve,reject)=>{const deadline=performance.now()+5000;const poll=()=>{if(Number(getComputedStyle(document.querySelector('.similar .site-card-reveal')).opacity)>.999)resolve(true);else if(performance.now()>deadline)reject(Error('card invisible'));else requestAnimationFrame(poll)};poll()})")
ab('screenshot',str(out/'daily-similar.png'))
print('PASS real daily browser login, career cards, visible-v2 event, search and similar page')
