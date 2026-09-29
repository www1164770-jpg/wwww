"""Explicit authorized one-time native daily activation. Never run at startup."""
import argparse,hashlib,json,os,secrets,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from db_pool import validate_database_config
from search_catalog import engine_from_environment,Catalog
import pymysql
from dotenv import dotenv_values,set_key
p=argparse.ArgumentParser();p.add_argument('action',choices=['schema','config','index']);a=p.parse_args()
cfg=validate_database_config();assert (cfg['host'],cfg['port'],cfg['database'])==('127.0.0.1',3306,'nav_site')
out=ROOT/'artifacts/daily-activation';backup=json.loads((out/'backup-manifest.json').read_text())
assert backup['all_tables_equal'] and hashlib.sha256(Path(backup['dump']).read_bytes()).hexdigest()==backup['sha256']
engine=engine_from_environment()
def save(name,data): (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
if a.action=='schema':
    from resource_migration import metadata
    from search_migration import preview,apply
    from scripts.feedback_migration import preview as feedback_preview,apply as feedback_apply
    # Add empty provenance tables only. No claims, identity links or tag associations.
    metadata.create_all(engine)
    with engine.connect() as conn:
        plan=preview(conn);assert not plan['missing_optional_tables'];save('search-migration-reviewed.json',plan)
        apply(conn,plan)
    save('feedback-migration-reviewed.json',feedback_preview())
    with pymysql.connect(**cfg) as conn:
        feedback_apply(conn)
        with conn.cursor() as c:
            for table,original in backup['tables'].items():
                c.execute(f'CHECKSUM TABLE `{table}`');assert c.fetchone()[1]==original['checksum'],table+' changed during schema migration'
            c.execute("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='nav_site' AND TRIGGER_NAME LIKE 'search_v2_%'");assert c.fetchone()[0]==21
    save('schema-result.json',{'source_legacy_tables_unchanged':True,'search_triggers':21,'provenance_rows_added':0,'tag_links_added':0,'feedback_gate':'20260926_feedback_v1'})
elif a.action=='config':
    from werkzeug.security import generate_password_hash
    private=Path(backup['backup_directory'])/'smoke-account.json'
    assert not private.exists(),'Do not overwrite an existing smoke identity'
    name='zhihangyu_daily_smoke_20260929';password=secrets.token_urlsafe(24)
    with pymysql.connect(**cfg) as conn,conn.cursor() as c:
        c.execute('SELECT id FROM users WHERE username=%s',(name,));assert c.fetchone() is None
        c.execute("INSERT INTO users(username,email,password_hash,status) VALUES(%s,%s,%s,'active')",(name,name+'@example.test',generate_password_hash(password)))
        user_id=c.lastrowid;conn.commit()
    private.write_text(json.dumps({'username':name,'password':password,'id':user_id}),encoding='utf-8')
    root=dotenv_values(ROOT/'.env');assert root.get('DOCKER_MEILI_MASTER_KEY')
    values={'MYSQL_HOST':'127.0.0.1','MYSQL_PORT':'3306','MYSQL_DATABASE':'nav_site','SEARCH_BACKEND':'database','SEARCH_SYNC_ENABLED':'1','MEILI_HOST':'http://127.0.0.1:17701','MEILI_MASTER_KEY':root['DOCKER_MEILI_MASTER_KEY'],'MEILI_INDEX':'websites_daily_v1','REDIS_URL':'redis://127.0.0.1:16380/6','RATELIMIT_STORAGE_URI':'redis://127.0.0.1:16380/5','RECOMMENDATION_FEEDBACK_ENABLED':'1','RECOMMENDATION_EXPOSURE_V2':'1','RECOMMENDATION_RERANK_ENABLED':'0','AI_REQUIREMENTS_MODEL_ENABLED':'0','RECOMMENDATION_METRICS_TEST_USER_IDS':str(user_id),'FLASK_DEBUG':'0','BACKEND_HOST':'127.0.0.1','BACKEND_PORT':'5000','FRONTEND_URL':'http://127.0.0.1:5173'}
    # Preserve any explicitly configured prior test exclusions; never infer real users.
    old=dotenv_values(ROOT/'backend/.env').get('RECOMMENDATION_METRICS_TEST_USER_IDS')
    if old:values['RECOMMENDATION_METRICS_TEST_USER_IDS']=','.join(dict.fromkeys([*old.split(','),str(user_id)]))
    for k,v in values.items():set_key(str(ROOT/'backend/.env'),k,v)
    save('configuration-result.json',{'values':{k:v for k,v in values.items() if k!='MEILI_MASTER_KEY'},'test_user_id':user_id,'test_username':name,'model_credentials_changed':False})
else:
    from search_service import Meili
    from search_sync import Sync
    assert os.environ['MEILI_INDEX']=='websites_daily_v1' and os.environ['MEILI_HOST']=='http://127.0.0.1:17701'
    sync=Sync(Catalog(engine),Meili(os.environ['MEILI_HOST'],os.environ['MEILI_MASTER_KEY'],os.environ['MEILI_INDEX']))
    indexes=sync.meili.request('GET','/indexes')['results'];assert not indexes,'New daily volume must be empty before first index initialization'
    with sync.lock():sync.task('POST','/indexes',{'uid':sync.meili.index,'primaryKey':'id'},target=sync.meili.index)
    result=sync.rebuild();check=sync.reconcile();assert not any(check[k] for k in ('missing','stale','not_public_or_removed'))
    save('index-result.json',{'rebuild':result,'reconcile':check,'state':sync.state()})
    set_key(str(ROOT/'backend/.env'),'SEARCH_BACKEND','meilisearch')
print(json.dumps({'action':a.action,'success':True,'database':'nav_site'}))
