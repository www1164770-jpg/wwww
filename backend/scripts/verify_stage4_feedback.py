"""Real MySQL isolation: transactional preferences, audit, APIs and rollback."""
import json,sys
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
import pymysql
from flask import Flask
from flask_jwt_extended import JWTManager,create_access_token
from db_pool import validate_database_config
from feedback_migration import apply,preview
from recommendation_stage4 import Preferences,Conflict,reorder
from v1_routes import register_v1_routes

def run(*, event_timestamp_default=True):
    cfg=validate_database_config()
    assert cfg['host'] in {'localhost','127.0.0.1','::1'}
    database='feedback_'+uuid4().hex[:12]+'_test'
    with pymysql.connect(**cfg) as conn,conn.cursor() as c:c.execute(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4')
    def connect():return pymysql.connect(**{**cfg,'database':database},cursorclass=pymysql.cursors.DictCursor)
    report={'database':database,'source_database_modified':False,'model_calls':0,'checks':[]}
    def check(ok,label):
        assert ok,label
        report['checks'].append(label)
    def query(sql,args=()):
        with connect() as conn,conn.cursor() as c:c.execute(sql,args);rows=list(c.fetchall());conn.commit();return rows
    for sql in [
        'CREATE TABLE users(id INT PRIMARY KEY,username VARCHAR(50),email VARCHAR(100),deleted_at DATETIME NULL) ENGINE=InnoDB',
        'CREATE TABLE websites(id INT PRIMARY KEY,name VARCHAR(100),url VARCHAR(255),status VARCHAR(20),enabled INT) ENGINE=InnoDB',
        'CREATE TABLE user_behavior_events(id BIGINT AUTO_INCREMENT PRIMARY KEY,user_id INT,website_id INT,event_type VARCHAR(32),source VARCHAR(64),recommendation_batch_id VARCHAR(128),questionnaire_version VARCHAR(64),profile_version VARCHAR(64),session_id VARCHAR(128),metadata_json JSON,created_at DATETIME DEFAULT CURRENT_TIMESTAMP) ENGINE=InnoDB',
        "INSERT INTO users VALUES(1,'fixture1','fixture1@invalid',NULL),(2,'fixture2','fixture2@invalid',NULL)",
        "INSERT INTO websites VALUES(1,'Fixture One','https://fixture.invalid/one','approved',1),(2,'Fixture Two','https://fixture.invalid/two','approved',1)",
    ]:
        if not event_timestamp_default:
            sql=sql.replace('created_at DATETIME DEFAULT CURRENT_TIMESTAMP','created_at DATETIME NULL')
        query(sql)
    with connect() as conn:apply(conn);apply(conn)
    check(len(query('SELECT * FROM recommendation_feedback_migrations'))==1,'migration apply twice is idempotent')
    app=Flask(__name__);app.config.update(TESTING=True,JWT_SECRET_KEY='isolated-stage4-test-key-more-than-32')
    JWTManager(app);register_v1_routes(app,connect)
    with app.app_context():tokens={n:{'Authorization':'Bearer '+create_access_token(identity='fixture'+str(n))} for n in (1,2)}
    client=app.test_client()
    check(client.get('/api/recommendation/preferences').status_code==401,'preferences require login')
    check(client.get('/api/recommendation/preferences',headers=tokens[1]).get_json()['data']['enabled'] is False,'rollout defaults disabled')
    app.config['RECOMMENDATION_FEEDBACK_ENABLED']=True
    def payload(sid=1,reason='irrelevant',revision=0,**extra):return {'website_id':sid,'reason':reason,'expected_revision':revision,'request_id':uuid4().hex,'recommendation_batch_id':'fixture-batch','algorithm_version':'phase1-v1','rerank_version':'baseline',**extra}
    def post(body,uid=1):return client.post('/api/recommendation/preferences',json=body,headers=tokens[uid])
    original=payload();response=post(original)
    check(response.status_code==200 and response.get_json()['data']['revision']==1,'feedback creates user preference')
    check(post(original).get_json()==response.get_json(),'identical retry returns original result')
    check(post(payload(revision=1)).get_json()['data']['revision']==1,'equivalent reason no-op does not renew or duplicate')
    check(len(query('SELECT * FROM user_behavior_events'))==1,'one audit event for effective transition')
    check(client.get('/api/recommendation/preferences',headers=tokens[2]).get_json()['data']['items']==[],'other user inherits no preferences')
    check(post(payload(user_id=2)).status_code==400,'client user_id rejected')
    check(post(payload(reason=['bad'])).status_code==400,'invalid reason type rejected')
    check(post(payload(reason=None)).status_code==409,'stale undo rejected')
    check(post(payload(reason=None,revision=1)).get_json()['data']['revision']==2,'undo advances revision and clears preference')
    check([r['event_type'] for r in query('SELECT event_type FROM user_behavior_events ORDER BY id')]==['feedback','feedback_undo'],'undo distinct from clicks and favorites')
    prefs=Preferences(connect);fixed=datetime(2026,9,26)
    row=prefs.change(1,payload(reason='later',revision=2),now=fixed)
    candidate={'id':1,'url':'https://fixture.invalid/one','status':'approved','enabled':1,'match_score':80,'match_evidence':[{'field':'tags'}]}
    check(reorder([candidate],prefs.list(1),now=fixed)==[],'temporary feedback suspends active recommendation')
    check(len(reorder([candidate],prefs.list(1),now=fixed+timedelta(days=31)))==1,'expiry restores without data deletion')
    # Independent concurrent connections contend on the authenticated user's lock.
    bodies=[payload(sid=2,reason='known'),payload(sid=2,reason='later')]
    def mutate(body):
        try:prefs.change(1,body);return 'saved'
        except Conflict:return 'conflict'
    with ThreadPoolExecutor(2) as workers:outcomes=list(workers.map(mutate,bodies))
    check(sorted(outcomes)==['conflict','saved'],'concurrent stale revisions cannot overwrite preference')
    # Audit insertion failure must roll back BOTH state and idempotency receipt.
    class CursorProxy:
        def __init__(self,c):self.c=c
        def __enter__(self):self.c.__enter__();return self
        def __exit__(self,*args):return self.c.__exit__(*args)
        def execute(self,sql,args=()):
            if sql.startswith('INSERT INTO user_behavior_events'):raise RuntimeError('injected isolated audit failure')
            return self.c.execute(sql,args)
        def __getattr__(self,k):return getattr(self.c,k)
    class ConnectionProxy:
        def __init__(self):self.c=connect()
        def cursor(self):return CursorProxy(self.c.cursor())
        def __getattr__(self,k):return getattr(self.c,k)
    try:Preferences(ConnectionProxy).change(2,payload())
    except RuntimeError:pass
    check(prefs.list(2)==[] and query('SELECT * FROM recommendation_feedback_operations WHERE user_id=2')==[],'audit failure rolls back preference and receipt')
    event={'website_id':1,'event_type':'impression','source':'personalized_recommendation','recommendation_batch_id':'visible-batch','session_id':'test-session','metadata':{'event_version':'visible-v2','visible_ratio':.5,'visible_ms':1000,'rerank_version':'diversity-v1'}}
    check(client.post('/api/behavior/events',json={**event,'metadata':{'event_version':'visible-v2'}},headers=tokens[1]).status_code==400,'v2 requires visibility context')
    first=client.post('/api/behavior/events',json=event,headers=tokens[1]);second=client.post('/api/behavior/events',json=event,headers=tokens[1])
    stored=query("SELECT created_at,metadata_json FROM user_behavior_events WHERE event_type='impression'")
    check(bool(stored) and all(r['created_at'] is not None and json.loads(r['metadata_json'])['collection_version']=='server-time-v1' for r in stored),'server timestamp and collection version independent of table default')
    check(first.status_code==200 and first.get_json()['data']['recorded'] and not second.get_json()['data']['recorded'],'visible events deduplicate server-side')
    concurrent_event={**event,'recommendation_batch_id':'concurrent-visible-batch'}
    def expose(_):
        with app.test_client() as c:return c.post('/api/behavior/events',json=concurrent_event,headers=tokens[1]).get_json()['data']['recorded']
    with ThreadPoolExecutor(2) as workers:recorded=list(workers.map(expose,range(2)))
    check(sorted(recorded)==[False,True],'concurrent impressions count once under MySQL snapshot isolation')
    event['metadata']={'event_version':'legacy-v1'}
    check(client.post('/api/behavior/events',json=event,headers=tokens[1]).get_json()['data']['recorded'],'old and new event versions remain distinct')
    before=query('SELECT * FROM recommendation_preferences')
    with connect() as conn:apply(conn,True)
    check(query('SELECT * FROM recommendation_preferences')==before,'rollback retains preference data and audit history')
    check(client.get('/api/recommendation/preferences',headers=tokens[1]).status_code==503,'rollback gate prevents reads/writes when rollout accidentally left on')
    with connect() as conn:apply(conn)
    check(prefs.list(1),'roll forward preserves effective preferences')
    report['status']='passed';return report

if __name__=='__main__':
    report=run();(ROOT/'docs/recommendation/stage4-isolated-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
