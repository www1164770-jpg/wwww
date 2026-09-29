"""Add six synthetic resources only to the existing named isolated rehearsal DB."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from db_pool import validate_database_config
import pymysql
manifest=json.loads((ROOT/'docs/release/resource-chain.json').read_text(encoding='utf-8'))
database='resource_chain_7a54fb93b0d4_test'
assert manifest['test_database']==database
cfg=validate_database_config();assert cfg['host'] in ('127.0.0.1','localhost')
with pymysql.connect(**{**cfg,'database':database}) as conn,conn.cursor() as c:
    c.execute('SELECT DATABASE()');assert c.fetchone()[0]==database
    c.execute('SELECT COUNT(*) FROM websites WHERE id BETWEEN 91001 AND 91006');assert c.fetchone()[0]==0, 'fixture already exists; do not overwrite'
    names=['专项源资源','专项同域付费产品','专项已确认别名','专项下架产品','专项未知收费产品','孤立空结果']
    for sid,name in enumerate(names,91001):
        c.execute('INSERT INTO websites(id,name,url,summary,description,category_id,status) VALUES(%s,%s,%s,%s,%s,1,%s)',(sid,name,f'http://127.0.0.1:15000/fixture/{sid}',name,name,'rejected' if sid==91004 else 'approved'))
    c.execute("INSERT INTO tags(name) VALUES('专项相似验收20260929')");tag=c.lastrowid
    for sid in range(91001,91006):c.execute('INSERT INTO site_tags(site_id,tag_id) VALUES(%s,%s)',(sid,tag))
    c.execute("INSERT INTO resource_identity_links(source_id,target_id,evidence,state) VALUES(91003,91001,'synthetic acceptance alias','active')")
    for sid,value in [(91001,'free'),(91002,'paid')]:
        c.execute("INSERT INTO resource_field_claims(site_id,field,value,source_kind,source_ref,verified_at,state) VALUES(%s,'pricing_model',%s,'manual','synthetic acceptance','2026-09-29T01:00:00Z','active')",(sid,value))
    conn.commit()
print(json.dumps({'database':database,'synthetic_ids':list(range(91001,91007)),'daily_database_written':False}))
