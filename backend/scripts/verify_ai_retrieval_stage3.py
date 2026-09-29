"""Real isolated MySQL + Meilisearch + Redis, deterministic model doubles.

Never contacts a model provider or imports app startup. Never migrates source DB.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT),str(ROOT/'tests')]
import pymysql
import redis
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from flask import Flask
from flask_jwt_extended import JWTManager,create_access_token
from db_pool import validate_database_config
from search_catalog import Catalog
from search_service import SearchService,Meili
from search_sync import Sync
from search_migration import apply,preview
from resource_migration import metadata
from v1_routes import register_v1_routes
from test_ai_retrieval_stage3 import valid_model,QUERY
from test_ai_site_recommend_v1 import AI_INVALID_QUERY_CASES
from backend.crawler.analysis.service import ModelFailure


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--create-isolated-test-db',required=True,action='store_true')
    args=parser.parse_args()
    cfg=validate_database_config()
    if cfg['host'] not in ('localhost','127.0.0.1','::1'): raise ValueError('Local isolated DB only')
    token=uuid4().hex[:12]; database='ai_retrieval_'+token+'_test'; index='stage3_test_'+token
    with pymysql.connect(**cfg) as conn,conn.cursor() as c:
        c.execute(f'CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    url=URL.create('mysql+pymysql',username=cfg['user'],password=cfg['password'],host=cfg['host'],port=cfg['port'],database=database)
    engine=create_engine(url,isolation_level='READ COMMITTED')
    meili=Meili('http://127.0.0.1:17700',index=index)
    service=SearchService(Catalog(engine),meili,redis.Redis(port=16379,socket_timeout=.3))
    sync=Sync(service.catalog,meili)
    report={'captured_at':datetime.now(timezone.utc).isoformat(),'database':database,'index':index,
            'source_database_modified':False,'model':'deterministic doubles; NO real provider call','real_model_verified':False,
            'sample_count':8,'checks':[],'responses':[],'request_timings':[],
            'cache_conditions':'Unique new test index starts cold; subsequent requests reuse its Redis candidates. No production performance claim.'}
    def check(ok,message):
        if not ok: raise AssertionError(message)
        report['checks'].append(message)
    def execute(sql,**params):
        with engine.begin() as c:c.execute(text(sql),params)
    try:
        with engine.begin() as c:
            for sql in [
                'CREATE TABLE websites(id INT PRIMARY KEY,name VARCHAR(100),url VARCHAR(255),summary TEXT,description TEXT,category_id INT,status VARCHAR(20),enabled INT,is_free INT,need_login INT,quality_score INT DEFAULT 0) ENGINE=InnoDB',
                'CREATE TABLE categories(id INT PRIMARY KEY,name VARCHAR(100),code VARCHAR(40),status VARCHAR(20)) ENGINE=InnoDB',
                'CREATE TABLE tags(id INT PRIMARY KEY,name VARCHAR(100)) ENGINE=InnoDB',
                'CREATE TABLE site_tags(id INT PRIMARY KEY AUTO_INCREMENT,site_id INT,tag_id INT) ENGINE=InnoDB',
                'CREATE TABLE site_occupations(id INT PRIMARY KEY AUTO_INCREMENT,site_id INT,occupation VARCHAR(100)) ENGINE=InnoDB',
                'CREATE TABLE users(id INT PRIMARY KEY,username VARCHAR(100),email VARCHAR(100),deleted_at DATETIME) ENGINE=InnoDB',
                'CREATE TABLE user_profiles(user_id INT PRIMARY KEY,occupation VARCHAR(100),interests TEXT) ENGINE=InnoDB',
            ]:c.exec_driver_sql(sql)
            metadata.create_all(c)
        with engine.connect() as c:apply(c,preview(c))
        execute("INSERT INTO categories VALUES(1,'科研','research','active'),(2,'开发','dev','active')")
        fixtures=[(1,'Plot Alpha','论文绘图',1,'free'),(2,'Plot Trial','论文绘图',1,'trial'),
                  (3,'Plot Unknown','论文绘图',1,None),(4,'API Bench','接口调试',2,'free'),
                  (5,'Hidden Plot','论文绘图',1,'free'),(6,'Plot Alias','论文绘图',1,'free'),
                  (7,'Plot Paid','论文绘图',1,'paid'),(8,'Paper Library','文献检索',1,'free')]
        for sid,name,summary,category,price in fixtures:
            execute('INSERT INTO websites VALUES(:id,:name,:url,:summary,:summary,:category,\'approved\',:enabled,1,NULL,0)',
                id=sid,name=name,url=f'https://fixture.invalid/products/{sid}',summary=summary,category=category,enabled=0 if sid==5 else 1)
            if price is not None:
                for field,value in [('pricing_model',price),('language','en' if sid==4 else 'zh'),('entry_requirements',json.dumps({'installation':'none','level':'beginner','platforms':['web']}))]:
                    execute("INSERT INTO resource_field_claims(site_id,field,value,source_kind,source_ref,verified_at,state) VALUES(:sid,:field,:value,'manual','synthetic-stage3-fixture','2026-09-25','active')",sid=sid,field=field,value=value)
        execute("INSERT INTO tags VALUES(1,'scientific_plot'),(2,'api_testing'),(3,'literature')")
        for sid in range(1,9):execute('INSERT INTO site_tags(site_id,tag_id) VALUES(:sid,:tag)',sid=sid,tag=2 if sid==4 else 3 if sid==8 else 1)
        execute("INSERT INTO resource_identity_links(source_id,target_id,evidence,state) VALUES(6,1,'synthetic approved alias fixture','active')")
        execute("INSERT INTO site_occupations(site_id,occupation) VALUES(4,'程序员'),(1,'学生')")
        execute("INSERT INTO users VALUES(1,'stage3_fixture','stage3@fixture.invalid',NULL)")
        execute("INSERT INTO user_profiles VALUES(1,'程序员','[\"开发\"]')")
        meili.wait(meili.request('POST','/indexes',{'uid':index,'primaryKey':'id'})['taskUid'])
        sync.rebuild();sync.once()
        app=Flask(__name__);app.config.update(TESTING=True,JWT_SECRET_KEY='stage3-isolated-test-secret-more-than-32',AI_REQUIREMENTS_MODEL=valid_model)
        JWTManager(app)
        register_v1_routes(app,lambda:pymysql.connect(**{**cfg,'database':database},cursorclass=pymysql.cursors.DictCursor),search_service=service)
        with app.app_context():headers={'Authorization':'Bearer '+create_access_token(identity='stage3_fixture')}
        client=app.test_client()
        def ai(query=QUERY,model=valid_model):
            app.config['AI_REQUIREMENTS_MODEL']=model
            started=time.perf_counter()
            response=client.post('/api/ai/site-recommend',json={'query':query},headers=headers)
            report['request_timings'].append({'query':query,'duration_ms':round((time.perf_counter()-started)*1000,3),'model':'double','sequence':len(report['request_timings'])+1})
            check(response.status_code==200,'AI success response: '+query)
            data=response.get_json()['data'];report['responses'].append({'query':query,'data':data})
            return data
        result=ai()
        check(result['items'][0]['id']==1 and result['items'][0]['match_status']=='full','hard requirements outrank conflicting programmer profile')
        by_id={r['id']:r for r in result['items']}
        check(6 not in by_id,'AI also excludes confirmed product aliases')
        check(by_id[2]['match_status']=='partial' and by_id[3]['match_status']=='unverified','trial is not fully free; missing verified fields remain unknown')
        check(5 not in by_id and 4 not in by_id and 8 not in by_id,'unpublished and unrelated resources excluded')
        check(all(r['url'].startswith('https://fixture.invalid/products/') for r in result['items']),'all identities/links originate from real fixture records')
        check(all(r['match_evidence'] for r in result['items']),'each reason has field evidence')
        check(ai('接口调试工具')['items'][0]['id']==4,'different task retrieves API resource through same search service')
        check(ai('不要付费，不需要中文也可以的接口调试工具')['items'][0]['match_status']=='full','negative fee and optional Chinese handled correctly')
        conflict=ai('免费但必须付费的论文绘图工具')
        check(conflict['items']==[] and conflict['clarifications'],'contradiction returns clarification, not arbitrary selection')
        timeout=lambda *_:(_ for _ in ()).throw(ModelFailure('timeout'))
        check(ai(model=timeout)['degraded'],'model timeout falls back to rules with explicit notice')
        check(ai(model=lambda *_:'not JSON')['degraded'],'invalid JSON structure falls back to rules')
        def invented(prompt,payload):
            return valid_model(prompt,payload) if 'baseline' in payload else {'explanations':[{'id':999,'url':'https://invented.invalid','evidence_ids':[0]}]}
        check(ai(model=invented)['items'][0]['id']==1,'fabricated model ID/link rejected without losing valid retrieval')
        execute("UPDATE websites SET enabled=0 WHERE id=1")
        check(1 not in [r['id'] for r in ai()['items']],'resource unpublished before async sync is hidden')
        execute("UPDATE websites SET enabled=1 WHERE id=1")
        similar=client.get('/api/sites/1/similar').get_json()['data']
        ids=[r['id'] for r in similar]
        check(1 not in ids and 6 not in ids and 5 not in ids and 8 not in ids,'similarity excludes self, confirmed alias, unpublished and unrelated category peer')
        check(7 in ids and next(r for r in similar if r['id']==7)['differences'],'paid alternative retained with explicit pricing difference')
        check(client.get('/api/sites/9999/similar').status_code==404,'similarity missing-resource API compatibility')
        check(ids==[r['id'] for r in client.get('/api/sites/1/similar').get_json()['data']],'similarity stable ordering')
        check(client.post('/api/ai/site-recommend',json={'query':QUERY}).status_code==401,'AI authentication unchanged')
        for payload,message in AI_INVALID_QUERY_CASES:
            response=client.post('/api/ai/site-recommend',json=payload,headers=headers)
            check(response.status_code==400 and response.get_json()=={'success':False,'code':400,'error_code':None,'legacy_code':0,'message':message,'msg':message,'data':{}},'exact seven-field error contract '+message)
        ordinary=client.get('/api/search?q=接口调试')
        check(ordinary.status_code==200 and ordinary.get_json()['data']['items'][0]['id']==4,'ordinary search independent of failed model')
        sync.once()
        empty,meta=service.retrieve('stage3_no_such_product_937', [('stage3_no_such_product_937',)])
        check(empty==[] and meta['source']=='meilisearch' and meta['fallbackReason'] is None,'normal zero results never cause database fallback')
        service.redis=redis.Redis(port=1,socket_connect_timeout=.1,socket_timeout=.1)
        rows,meta=service.retrieve('接口调试',[('接口调试',)])
        check([r['id'] for r in rows]==[4] and meta['source']=='meilisearch','Redis failure preserves Meilisearch retrieval')
        service.meili=Meili('http://127.0.0.1:1',index=index,timeout=.1);service.redis=None
        fallback=client.get('/api/search?q=接口调试').get_json()['data']
        check(fallback['retrieval']['source']=='database' and fallback['items'][0]['id']==4,'ordinary search transport failure still falls back to database')
        report['status']='passed'
    except Exception as exc:
        report.update(status='failed',failure=type(exc).__name__+': '+str(exc));raise
    finally:
        path=ROOT/'docs/recommendation/stage3-isolated-verification.json'
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
        print(json.dumps({'database':database,'status':report.get('status'),'checks':len(report['checks'])}))


if __name__=='__main__':main()
