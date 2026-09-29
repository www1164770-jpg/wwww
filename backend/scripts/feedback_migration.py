"""Versioned, non-destructive stage4 migration. CLI writes isolated DBs only."""
import argparse,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from recommendation_stage4 import MIGRATION

DDL=[
'''CREATE TABLE IF NOT EXISTS recommendation_feedback_migrations(version VARCHAR(64) PRIMARY KEY,active INT NOT NULL) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS recommendation_preferences(user_id INT NOT NULL,website_id INT NOT NULL,reason VARCHAR(20) NULL,revision BIGINT NOT NULL,expires_at DATETIME NULL,updated_at DATETIME NOT NULL,PRIMARY KEY(user_id,website_id)) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS recommendation_feedback_operations(user_id INT NOT NULL,request_id VARCHAR(64) NOT NULL,fingerprint TEXT NOT NULL,result_json TEXT NOT NULL,PRIMARY KEY(user_id,request_id)) ENGINE=InnoDB''']

def preview(rollback=False):
    return {'version':MIGRATION,'action':'rollback' if rollback else 'apply','statements': ["UPDATE recommendation_feedback_migrations SET active=0 WHERE version='"+MIGRATION+"'"] if rollback else DDL+['Register active migration with idempotent upsert'],
            'data_deletion':False,'rollback':'Disable migration gate; retain all preferences, operations and behavior audit events. Disable rollout flags first.'}

def apply(conn,rollback=False):
    with conn.cursor() as c:
        c.execute('SHOW TABLES LIKE %s',('user_behavior_events',))
        if not c.fetchone():raise ValueError('existing behavior event table required')
        if rollback:c.execute('UPDATE recommendation_feedback_migrations SET active=0 WHERE version=%s',(MIGRATION,))
        else:
            for sql in DDL:c.execute(sql)
            c.execute('INSERT INTO recommendation_feedback_migrations(version,active) VALUES(%s,1) ON DUPLICATE KEY UPDATE active=1',(MIGRATION,))
    conn.commit()

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['preview','apply','rollback-preview','rollback']);p.add_argument('--database');p.add_argument('--preview',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    plan=preview(a.action.startswith('rollback'))
    if a.action in {'apply','rollback'}:
        if not a.database or not re.fullmatch(r'feedback_[0-9a-f]{12}_test',a.database):p.error('only isolated feedback_<12hex>_test writes allowed')
        if not a.preview or json.loads(a.preview.read_text(encoding='utf-8'))!=plan:p.error('matching reviewed preview required')
        import pymysql
        from db_pool import validate_database_config
        cfg=validate_database_config()
        if cfg['host'] not in {'127.0.0.1','localhost','::1'}:p.error('local test DB only')
        with pymysql.connect(**{**cfg,'database':a.database}) as conn:apply(conn,a.action=='rollback')
    a.output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
