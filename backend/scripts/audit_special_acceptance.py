"""Read-only daily configuration and isolated specialty evidence audit."""
import sys,json,os
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from db_pool import validate_database_config
from dotenv import dotenv_values
import pymysql
out=ROOT/'artifacts/local-integration';cfg=validate_database_config()
report={'captured_at':datetime.now(timezone.utc).isoformat(),'daily_target':{k:cfg[k] for k in ('host','port','database')},'config_files':{p:{'exists':(ROOT/p).exists(),'configured_keys':[k for k,v in dotenv_values(ROOT/p).items() if v] if (ROOT/p).exists() else []} for p in ['backend/.env','.env']},'model_key_present':bool(os.getenv('DEEPSEEK_API_KEY'))}
with pymysql.connect(**cfg,cursorclass=pymysql.cursors.DictCursor) as conn,conn.cursor() as c:
    c.execute('START TRANSACTION READ ONLY');c.execute('SHOW TABLES');tables={next(iter(r.values())) for r in c.fetchall()};report['daily_migration_tables']={t:t in tables for t in ['resource_field_claims','resource_identity_links','resource_quality_changes','search_sync_state','outbox_events','recommendation_feedback_migrations','recommendation_preferences']};conn.rollback()
database='resource_chain_7a54fb93b0d4_test'
assert json.loads((ROOT/'docs/release/resource-chain.json').read_text(encoding='utf-8'))['test_database']==database
assert cfg['host'] in ('localhost','127.0.0.1')
with pymysql.connect(**{**cfg,'database':database},cursorclass=pymysql.cursors.DictCursor) as conn,conn.cursor() as c:
    c.execute('START TRANSACTION READ ONLY');c.execute("SELECT id,user_id,event_type,website_id,recommendation_batch_id,metadata_json,created_at FROM user_behavior_events WHERE recommendation_batch_id LIKE 'special-%' ORDER BY id");report['isolated_exposure_events']=c.fetchall();c.execute('SELECT id,username FROM users WHERE id IN (1,2)');report['synthetic_accounts']=c.fetchall();c.execute('SELECT user_id,site_id FROM favorites WHERE site_id=91002');report['restored_fixture_favorites']=c.fetchall();conn.rollback()
clock=json.loads((out/'visibility-browser-clock.json').read_text(encoding='utf-8-sig'));native=json.loads((out/'visibility-native.json').read_text(encoding='utf-8-sig'))
rows=report['isolated_exposure_events'];actual=[r for r in rows if r['recommendation_batch_id']==clock['batch']];assert len(actual)==2 and {r['user_id'] for r in actual}=={1,2}
assert len([r for r in rows if r['recommendation_batch_id']==native['batch']])==1
report['assertions']={'clock_batch_one_per_account':True,'native_batch_one_event':True,'fixture_favorites_restored':not report['restored_fixture_favorites']}
(out/'special-final-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['config_files','isolated_exposure_events']},ensure_ascii=False))
