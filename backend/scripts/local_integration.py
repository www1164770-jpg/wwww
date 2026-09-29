"""Local-only release rehearsal on the freshly created resource-chain fixture.

No source data copy. Supply the fixture created by verify_resource_chain in this
run; this script never targets the configured application database.
"""
import argparse,json,os,re,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from db_pool import validate_database_config

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','serve','worker']);p.add_argument('--database',required=True)
    p.add_argument('--new-policy',action='store_true')
    p.add_argument('--feedback-delay-seconds',type=int,choices=range(31),default=0,help='Isolated browser fault injection; delays feedback POST only')
    p.add_argument('--response-gates',action='store_true',help='Test-only file-controlled response barriers, real auth and route bodies unchanged')
    a=p.parse_args()
    if a.action == 'serve':
        # Windows can retain a prior Flask listener after its shell exits. Never
        # mistake that process's flags for the newly requested rehearsal mode.
        import socket
        with socket.socket() as listener_check:
            listener_check.settimeout(1)
            if listener_check.connect_ex(('127.0.0.1',15000)) == 0:
                raise RuntimeError('port 15000 already has a listener; identify and stop only your test server first')
    cfg=validate_database_config();source=cfg['database']
    if not re.fullmatch(r'resource_chain_[a-f0-9]{12}_test',a.database) or cfg['host'] not in ('localhost','127.0.0.1'):raise ValueError('local resource-chain fixture only')
    manifest=json.loads((ROOT/'docs/release/resource-chain.json').read_text(encoding='utf-8'))
    if manifest['test_database']!=a.database:raise ValueError('database must match this run manifest')
    os.environ.update(MYSQL_DATABASE=a.database,DB_NAME=a.database,MEILI_HOST='http://127.0.0.1:17700',MEILI_INDEX='stage2_test_release_'+a.database,
        REDIS_URL='redis://127.0.0.1:16379/7',SEARCH_BACKEND='meilisearch',SEARCH_SYNC_ENABLED='1',
        RECOMMENDATION_RERANK_ENABLED=str(int(a.new_policy)),RECOMMENDATION_FEEDBACK_ENABLED=str(int(a.new_policy)),RECOMMENDATION_EXPOSURE_V2=str(int(a.new_policy)),
        JWT_SECRET_KEY='local-integration-only-long-test-key',RECOMMENDATION_METRICS_TEST_USER_IDS='1,2,3,4')
    # db_pool snapshots configuration at import. Reload before importing app;
    # assert the actual pooled DB before allowing any browser mutation.
    import importlib,db_pool
    importlib.reload(db_pool)
    with db_pool.get_connection() as guarded, guarded.cursor() as cursor:
        cursor.execute('SELECT DATABASE() AS db')
        if cursor.fetchone()['db'] != a.database:raise RuntimeError('isolation guard failed')
    import pymysql
    from search_catalog import engine_from_environment,Catalog
    from search_service import Meili
    from search_sync import Sync
    engine=engine_from_environment();sync=Sync(Catalog(engine),Meili(os.environ['MEILI_HOST'],index=os.environ['MEILI_INDEX']))
    if a.action=='prepare':
        from werkzeug.security import generate_password_hash
        from resource_migration import metadata
        from search_migration import preview,apply
        from scripts.feedback_migration import apply as feedback_apply
        with pymysql.connect(**cfg,cursorclass=pymysql.cursors.DictCursor) as conn,conn.cursor() as c:
            c.execute('SELECT TABLE_NAME FROM information_schema.tables WHERE table_schema=%s',(source,))
            for row in c.fetchall():
                table=row['TABLE_NAME']
                if not re.fullmatch(r'\w+',table):raise ValueError('table identifier')
                c.execute(f'CREATE TABLE IF NOT EXISTS `{a.database}`.`{table}` LIKE `{source}`.`{table}`')
        with pymysql.connect(**{**cfg,'database':a.database},cursorclass=pymysql.cursors.DictCursor) as conn,conn.cursor() as c:
            c.execute("UPDATE users SET password_hash=%s,status='active'",(generate_password_hash('Local-Integration-Only-2026!'),))
            for i in range(10,50):
                topic='接口调试 HTTP API' if i%2 else '文献检索 scholarly research'
                c.execute("INSERT INTO websites(id,name,url,category_id,summary,description,status) VALUES(%s,%s,%s,1,%s,%s,'approved') ON DUPLICATE KEY UPDATE summary=VALUES(summary)",(i,f'Fixture {i} {topic}',f'http://127.0.0.1:15000/fixture/{i}',topic,topic))
                tag='api' if i%2 else 'literature_search'
                c.execute('INSERT IGNORE INTO site_tags(site_id,tag_id) SELECT %s,id FROM tags WHERE name=%s',(i,tag))
                c.execute('INSERT IGNORE INTO site_occupations(site_id,occupation,weight) VALUES(%s,%s,1)',(i,'backend_engineer' if i%2 else 'graduate_student'))
            conn.commit();feedback_apply(conn)
        metadata.create_all(engine)
        with engine.connect() as conn:
            plan=preview(conn)
            (ROOT/'docs/release/search-migration-preview.json').write_text(json.dumps(plan,indent=2,default=str),encoding='utf-8')
            apply(conn,plan)
        try:sync.meili.request('GET','/indexes/'+os.environ['MEILI_INDEX'])
        except Exception:
            with sync.lock():sync.task('POST','/indexes',{'uid':os.environ['MEILI_INDEX'],'primaryKey':'id'},target=os.environ['MEILI_INDEX'])
        sync.rebuild();print(json.dumps({'database':a.database,'index':os.environ['MEILI_INDEX'],'prepared':True}))
    elif a.action=='worker':
        while True:sync.once();time.sleep(.5)
    else:
        from app import app
        if a.response_gates:
            from scripts.integration_response_gate import install
            install(app,ROOT/'artifacts/local-integration/gates')
        if a.feedback_delay_seconds:
            from flask import request
            @app.before_request
            def isolated_feedback_delay():
                if request.path == '/api/recommendation/preferences' and request.method == 'POST':
                    time.sleep(a.feedback_delay_seconds)
        @app.get('/fixture/<int:site_id>')
        def fixture(site_id):return 'Local integration destination '+str(site_id)
        app.run(host='127.0.0.1',port=15000,use_reloader=False,debug=False)

if __name__=='__main__':main()
