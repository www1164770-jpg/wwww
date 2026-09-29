"""Targeted acceptance through the existing agent-browser CLI, never a browser SDK."""
import json, os, subprocess, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/local-integration'
CLI=Path(os.environ['TEMP'])/'zhihangyu-integration-tools/node_modules/agent-browser/bin/agent-browser-win32-x64.exe'
SESSION=os.environ.get('SPECIAL_BROWSER_SESSION','special3')
log=json.loads((OUT/'special-browser-log.json').read_text(encoding='utf-8')) if (OUT/'special-browser-log.json').exists() else []
def ab(*args,script=None):
    result=subprocess.run([str(CLI),'--session',SESSION,*args],input=script,text=True,encoding='utf-8',capture_output=True)
    log.append({'command':list(args),'output':result.stdout,'stderr':result.stderr,'code':result.returncode})
    (OUT/'special-browser-log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stderr)
    return result.stdout
def js(source):
    out=ab('eval','--stdin',script=source)
    return json.loads(out)
def snap():return ab('snapshot','-i')
def click(label,kind='button'):
    tree=snap();match=re.search(r'- '+kind+' "'+re.escape(label)+r'"[^\n]*\[[^\]\n]*ref=(e\d+)\]',tree)
    assert match,(label,tree)
    ab('click','@'+match[1])
def check(name,condition):
    assert condition,name
    log.append({'assertion':name,'passed':True})
    (OUT/'special-browser-log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
def loaded():ab('wait','.similar')
def main():
    ab('open','http://127.0.0.1:15173/site/91001');loaded()
    text=ab('get','text','.similar')
    check('same-domain paid product and unknown retained, current/alias/unpublished excluded',all(x in text for x in ['专项同域付费产品','专项未知收费产品','收费模式不同：当前资源为完全免费，此资源为付费','此资源收费模式待核实','共同标签']) and all(x not in text for x in ['专项源资源','专项已确认别名','专项下架产品']))
    ab('network','route','**/api/sites/91001/similar','--abort');ab('reload');loaded()
    check('failure visible', '相似资源加载失败' in ab('get','text','.similar'))
    ab('screenshot',str(OUT/'similar-failure-fixed.png'))
    ab('network','unroute','**/api/sites/91001/similar');click('重试')
    ab('wait','--fn',"!document.querySelector('.similar [role=alert]')")
    check('retry completed real response','专项同域付费产品' in ab('get','text','.similar'))
    # Pick the first actual detail link found in the DOM/snapshot.
    tree=snap();ref=re.search(r'- link "查看详情" \[ref=(e\d+)\]',tree)[1]
    ab('scrollintoview','@'+ref)
    ab('eval','--stdin',script="document.querySelector('.similar a[href=\"/site/91002\"]').click()")
    ab('wait','--fn',"location.pathname==='/site/91002' && [...document.querySelectorAll('h1')].some(e=>e.textContent.includes('专项同域付费产品'))")
    check('SPA detail heading follows route', '专项同域付费产品' in ab('get','text','h1'))
    ab('open','http://127.0.0.1:15173/site/91006');loaded()
    check('empty result', '暂无相似网站' in ab('get','text','.similar'))
    ab('screenshot',str(OUT/'similar-empty.png'))
    ab('open','http://127.0.0.1:15173/site/91001');loaded()
    for width,height,name in [(1440,1000,'desktop'),(390,844,'narrow')]:
        ab('set','viewport',str(width),str(height));ab('scrollintoview','.similar')
        geometry=js("""(()=>{const cards=[...document.querySelectorAll('.similar .site-card')];return {overflow:document.documentElement.scrollWidth>innerWidth,cards:cards.map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,width:r.width}}),width:innerWidth}})()""")
        check(name+' horizontal bounds',not geometry['overflow'] and all(c['left']>=0 and c['right']<=width for c in geometry['cards']))
        ab('screenshot',str(OUT/f'similar-{name}.png'))
    print('PASS targeted similarity routing, filters, evidence, failure/retry, empty, desktop/narrow bounds')
if __name__=='__main__':main()
