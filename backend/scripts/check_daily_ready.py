"""Read-only migration/config readiness gate for start.bat."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from dotenv import load_dotenv
load_dotenv(ROOT/'backend/.env',override=True)
from db_pool import validate_database_config
import pymysql
cfg=validate_database_config()
assert (cfg['host'],cfg['port'],cfg['database'])==('127.0.0.1',3306,'nav_site'),'Unexpected daily database'
assert os.getenv('AI_REQUIREMENTS_MODEL_ENABLED')=='0' and os.getenv('RECOMMENDATION_RERANK_ENABLED')=='0'
assert os.getenv('SEARCH_BACKEND') in ('database','meilisearch')
assert os.getenv('MEILI_INDEX')=='websites_daily_v1' and os.getenv('MEILI_HOST')=='http://127.0.0.1:17701'
assert os.getenv('REDIS_URL')=='redis://127.0.0.1:16380/6'
assert os.getenv('RECOMMENDATION_METRICS_TEST_USER_IDS','').strip(),'Explicit test exclusions required'
with pymysql.connect(**cfg) as conn,conn.cursor() as c:
    c.execute('SELECT DATABASE()');assert c.fetchone()[0]=='nav_site'
    c.execute('SELECT revision,indexed_revision FROM search_sync_state WHERE id=1');assert c.fetchone()
    c.execute("SELECT active FROM recommendation_feedback_migrations WHERE version='20260926_feedback_v1'");assert c.fetchone()==(1,)
    c.execute("SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA='nav_site' AND TRIGGER_NAME LIKE 'search_v2_%'");assert c.fetchone()==(21,)
print('Daily readiness OK: local nav_site, reviewed schema, protected flags, dedicated index/cache')
