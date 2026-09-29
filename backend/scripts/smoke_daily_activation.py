"""One brief real HTTP smoke under the explicitly excluded daily test account."""
import json,os,sys,time
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'tests'),str(ROOT)]
import requests,pymysql
from db_pool import validate_database_config
from test_resource_quality_stage1 import API
from search_catalog import engine_from_environment,Catalog
from search_service import Meili
from search_sync import Sync
out=ROOT/'artifacts/daily-activation';backup=json.loads((out/'backup-manifest.json').read_text())
account=json.loads((Path(backup['backup_directory'])/'smoke-account.json').read_text())
assert str(account['id']) in os.environ['RECOMMENDATION_METRICS_TEST_USER_IDS'].split(',')
cfg=validate_database_config();assert (cfg['host'],cfg['port'],cfg['database'])==('127.0.0.1',3306,'nav_site')
report={'test_user_id':account['id'],'checks':[]};session=requests.Session()
def call(method,path,**kwargs):
    r=session.request(method,'http://127.0.0.1:5000/api'+path,timeout=20,**kwargs)
    assert r.status_code==200,(path,r.status_code)
    return r.json()['data']
def check(name,value=True):
    assert value,name;report['checks'].append(name)
    (out/'smoke-http.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
login=call('POST','/auth/login',json={'account':account['username'],'password':account['password']})
session.headers['Authorization']='Bearer '+login['access_token'];check('login')
call('POST','/questionnaire/submit',json={'version':3,'answers':API})
career=call('GET','/career/recommendations');check('career recommendations',bool(career.get('careers')))
sites=[s for c in career['careers'] for s in c.get('sites',c.get('websites',[]))]
check('feedback + visible-v2 enabled; baseline rerank retained',bool(sites) and all(s.get('feedback_enabled') and s.get('event_version')=='visible-v2' and s.get('rerank_version')=='baseline' for s in sites))
sid=sites[0]['id'];report['site_id']=sid
first=call('GET','/sites/search',params={'q':'GitHub','page_size':10});second=call('GET','/sites/search',params={'q':'GitHub','page_size':10})
report['search_before']=[first.get('retrieval'),second.get('retrieval')]
check('public Meili search with Redis hot cache',bool(first['items']) and second['retrieval']['source']=='meilisearch' and second['retrieval']['cached'])
detail=call('GET',f'/sites/{sid}');similar=call('GET',f'/sites/{sid}/similar')
check('detail and similar resources',detail['id']==sid and bool(similar) and all(s['id']!=sid for s in similar))
report['similar_ids']=[s['id'] for s in similar]
ai=call('POST','/ai/site-recommend',json={'query':'免费、中文的接口调试工具'})
check('rule retrieval with model disabled',ai['requirements']['source']!='model')
report['ai_mode']={'source':ai['requirements']['source'],'degraded':ai.get('degraded')}
call('POST',f'/sites/{sid}/favorite',json={});check('favorite add')
call('DELETE',f'/sites/{sid}/favorite');check('favorite restored')
payload={'website_id':sid,'reason':'later','expected_revision':0,'request_id':uuid4().hex,'recommendation_batch_id':'daily-smoke-'+uuid4().hex,'algorithm_version':'phase1-v1','rerank_version':'baseline'}
pref=call('POST','/recommendation/preferences',json=payload);check('negative feedback',pref['reason']=='later')
restored=call('POST','/recommendation/preferences',json={**payload,'reason':None,'expected_revision':pref['revision'],'request_id':uuid4().hex})
check('feedback restore',restored['reason'] is None)
sync=Sync(Catalog(engine_from_environment()),Meili(os.environ['MEILI_HOST'],os.environ['MEILI_MASTER_KEY'],os.environ['MEILI_INDEX']))
deadline=time.monotonic()+20
while True:
    state=sync.state()
    with pymysql.connect(**cfg) as conn,conn.cursor() as c:
        c.execute("SELECT COUNT(*) FROM outbox_events WHERE event_type='search.changed' AND status<>'processed'");pending=c.fetchone()[0]
    if state['revision']==state['indexed_revision'] and pending==0:break
    if time.monotonic()>deadline:raise RuntimeError('worker did not converge')
    time.sleep(.2)
reconcile=sync.reconcile();check('worker revision and index converge',state['revision']>0 and not any(reconcile[k] for k in ('missing','stale','not_public_or_removed')))
new=call('GET','/sites/search',params={'q':'GitHub','page_size':10});hot=call('GET','/sites/search',params={'q':'GitHub','page_size':10})
check('cache revision updates after committed writes',new['dataVersion']!=first['dataVersion'] and hot['retrieval']['cached'])
report.update(state=state,reconcile=reconcile,search_after=[new['retrieval'],hot['retrieval']],status='passed')
check('all requested HTTP checks completed')
print(json.dumps({'status':'passed','checks':report['checks'],'test_user_id':account['id'],'site_id':sid},ensure_ascii=False))
