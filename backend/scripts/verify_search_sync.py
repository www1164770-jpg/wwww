"""Fixed synthetic fixtures against isolated MySQL, Meilisearch and Redis.

Never reads/copies application resources or users; creates a fresh *_test schema
and a stage2_test_* index. Leaves artifacts intact for review.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import subprocess
import time
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
import pymysql
import redis
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from db_pool import validate_database_config
from search_catalog import Catalog
from search_migration import preview, apply
from search_service import Meili, SearchService, SearchUnavailable, SearchConfigurationError
from search_sync import Sync
from v1_routes import register_v1_routes, search_term_groups, rank_search_sites


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--create-isolated-test-db", required=True, action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/search/stage2-verification.json")
    args = parser.parse_args()
    cfg = validate_database_config()
    if cfg["host"] not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Local test DB only")
    token = uuid4().hex[:12]
    database, index = "search_sync_" + token + "_test", "stage2_test_" + token
    base = pymysql.connect(**cfg)
    with base.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    base.close()
    engine = create_engine(URL.create("mysql+pymysql", username=cfg["user"], password=cfg["password"], host=cfg["host"], port=cfg["port"], database=database), isolation_level="READ COMMITTED")
    catalog = Catalog(engine)
    meili = Meili("http://127.0.0.1:17700", index=index)
    cache = redis.Redis.from_url("redis://127.0.0.1:16379/0", socket_timeout=.3)
    service = SearchService(catalog, meili, cache)
    sync = Sync(catalog, meili)
    report = {"captured_at":datetime.now(timezone.utc).isoformat(),"database": database, "index": index, "source_database_modified": False,
              "environment": {"mysql": "local", "meilisearch": "isolated Docker v1.12 port 17700", "redis": "isolated Docker 7 port 16379"},
              "initial_sample_count": 8, "checks": [], "queries": []}
    def check(value, message):
        if not value:
            raise AssertionError(message)
        report["checks"].append(message)
    def execute(sql, **params):
        with engine.begin() as conn:
            conn.execute(text(sql), params)
    def query(q, **kw):
        items, meta = service.retrieve(q, search_term_groups(q), **kw)
        ranked = rank_search_sites(items, q, kw.get("sort", "relevance"))
        return [r["id"] for r in ranked], meta
    try:
        with engine.connect() as conn:
            report["environment"]["mysql_version"] = conn.execute(text("SELECT VERSION()")).scalar()
        report["environment"]["meilisearch_version"] = meili.request("GET","/version")["pkgVersion"]
        report["environment"]["redis_version"] = cache.info("server")["redis_version"]
        report["environment"]["python_version"] = sys.version.split()[0]
        with engine.begin() as conn:
            for sql in [
                "CREATE TABLE categories(id INT PRIMARY KEY,name VARCHAR(100),code VARCHAR(100),status VARCHAR(20)) ENGINE=InnoDB",
                "CREATE TABLE websites(id INT PRIMARY KEY,name VARCHAR(100),url VARCHAR(255),aliases VARCHAR(255),summary TEXT,description TEXT,use_cases TEXT,category_id INT,status VARCHAR(20),enabled INT,click_count INT DEFAULT 0,recommend_level INT DEFAULT 0,quality_score INT DEFAULT 0,updated_at DATETIME) ENGINE=InnoDB",
                "CREATE TABLE tags(id INT PRIMARY KEY,name VARCHAR(100)) ENGINE=InnoDB",
                "CREATE TABLE site_tags(id INT PRIMARY KEY AUTO_INCREMENT,site_id INT,tag_id INT) ENGINE=InnoDB",
                "CREATE TABLE site_occupations(id INT PRIMARY KEY AUTO_INCREMENT,site_id INT,occupation VARCHAR(100)) ENGINE=InnoDB",
                "CREATE TABLE users(id INT PRIMARY KEY,username VARCHAR(100),email VARCHAR(100),deleted_at DATETIME) ENGINE=InnoDB",
                "CREATE TABLE user_profiles(user_id INT PRIMARY KEY,occupation VARCHAR(100),interests TEXT) ENGINE=InnoDB",
            ]:
                conn.exec_driver_sql(sql)
        with engine.connect() as conn:
            migration = preview(conn)
            artifact = ROOT / "artifacts" / database
            artifact.mkdir(parents=True,exist_ok=True)
            (artifact/"migration-preview.json").write_text(json.dumps(migration,ensure_ascii=False,indent=2),encoding="utf-8")
            apply(conn, migration)
            second = preview(conn)
            check(not any(sql.startswith("CREATE TRIGGER") for sql in second["statements"]), "migration repeat creates no duplicate triggers")
        execute("INSERT INTO categories VALUES(1,'研究','research','active'),(2,'开发','dev','active')")
        fixtures = [(1,"Paper Atlas","文献检索","学术文献检索工具",1,"approved",1),
                    (2,"API Bench","接口调试","接口调试工具",2,"approved",1),
                    (3,"Vue","vue framework","前端框架",2,"approved",1),
                    (4,"Vue Theme","theme","Vue 主题",2,"approved",1),
                    (5,"Hidden API","隐藏","接口调试",2,"approved",0),
                    (6,"Pending Paper","待审","文献检索",1,"pending",1),
                    (7,"Paper Notes","notes","文献整理",1,"approved",1),
                    (8,"Case API","case","接口文档",2,"approved",1)]
        for sid,name,alias,summary,category,status,enabled in fixtures:
            execute("INSERT INTO websites(id,name,url,aliases,summary,description,use_cases,category_id,status,enabled,click_count,updated_at) VALUES(:id,:name,:url,:alias,:summary,:summary,:summary,:category,:status,:enabled,:clicks,:updated)",
                    id=sid,name=name,url=f"https://fixture.invalid/Product{sid}",alias=alias,summary=summary,category=category,status=status,enabled=enabled,clicks=999999 if sid==4 else 1,updated='2026-09-26' if sid==7 else '2026-09-25')
        execute("INSERT INTO tags VALUES(1,'literature'),(2,'api_test')")
        execute("INSERT INTO site_tags(site_id,tag_id) VALUES(1,1),(2,2)")
        execute("INSERT INTO site_occupations(site_id,occupation) VALUES(1,'科研人员'),(2,'后端开发')")
        before = sync.state()["revision"]
        with engine.connect() as conn:
            conn.execute(text("UPDATE websites SET name='rollback' WHERE id=1"))
            conn.rollback()
        check(sync.state()["revision"]==before, "business rollback also rolls back revision and outbox event")
        meili.wait(meili.request("POST", "/indexes", {"uid":index,"primaryKey":"id"})["taskUid"])
        built = sync.rebuild()
        check(built["swapped"], "temporary index settings/data validated before successful atomic swap")
        check(len(meili.documents())==6, "only six approved enabled resources enter public index")
        check(sync.once()["processed"]>0, "existing outbox batch processed only after successful task completion")
        check(sync.once()["processed"]==0, "repeat worker is idempotent")
        with sync.lock():
            try:
                Sync(catalog,meili).once()
                raise AssertionError("concurrent worker was not serialized")
            except SearchUnavailable:
                check(True,"concurrent worker cannot submit while another owns database lock")
        for q,expected in [("Paper Atlas",1),("文献检索",1),("literature",1),("接口调试",2),("科研人员",1),("Vue",3)]:
            for condition in ("cold", "warm"):
                ids, meta = query(q)
                check(ids and ids[0]==expected, f"{q} {condition} expected top result {expected}")
                check(meta["cached"] == (condition=="warm"), f"{q} {condition} cache state")
                report["queries"].append({"query":q,"expected_top_id":expected,"actual_ids":ids,"condition":condition,**meta})
        ids,meta=query("notfoundxyz987")
        check(ids==[] and meta["source"]=="meilisearch" and meta["fallbackReason"] is None, "healthy zero results never trigger DB fault fallback")
        check(query("接口",category=1)[0]==[], "category filter prevents cross-category result")
        # Actual Flask API paging/ordering contracts with the shared production service.
        app=Flask(__name__); app.config.update(TESTING=True,JWT_SECRET_KEY="stage2-search-test-secret-at-least-32")
        JWTManager(app)
        test_cfg={**cfg,"database":database}
        register_v1_routes(app,lambda:pymysql.connect(**test_cfg,cursorclass=pymysql.cursors.DictCursor),search_service=service)
        client=app.test_client()
        execute("INSERT INTO users VALUES(1,'stage2_fixture','stage2@fixture.invalid',NULL)")
        execute("INSERT INTO user_profiles VALUES(1,'科研人员','[]')")
        with app.app_context():
            auth={"Authorization":"Bearer "+create_access_token(identity="stage2_fixture")}
        ai=client.post("/api/ai/site-recommend",json={"query":"文献检索"},headers=auth)
        check(ai.status_code==200 and ai.get_json()["data"]["items"][0]["id"]==1,"AI route uses shared candidates with existing final ranking")
        for payload in ({},{"query":None},{"query":123},{"query":"   "},{"query":"编"},{"query":"x"*501}):
            invalid=client.post("/api/ai/site-recommend",json=payload,headers=auth)
            check(invalid.status_code==400 and invalid.get_json()["success"] is False and invalid.get_json()["code"]==400,"AI invalid query contract remains HTTP/business 400")
        p1=client.get("/api/search?q=Paper&page_size=1&page=1").get_json()["data"]
        p2=client.get("/api/search?q=Paper&page_size=1&page=2").get_json()["data"]
        check(p1["pagination"]["total"]==2 and p1["items"][0]["id"]!=p2["items"][0]["id"], "route pagination uses current validated candidates without holes")
        check(client.get("/api/search/version").status_code==200,"frontend version validation endpoint")
        for sort in ("name","latest","recommend","relevance"):
            check(client.get('/api/search?q=Paper&sort='+sort).status_code==200, "existing sort accepted: "+sort)
        for q,sort,expected in [('Paper','name',[1,7]),('Paper','latest',[7,1]),('Vue','recommend',[4,3]),('Vue','relevance',[3,4])]:
            actual=client.get('/api/search',query_string={'q':q,'sort':sort}).get_json()['data']['items']
            check([r['id'] for r in actual]==expected,'exact sort order '+q+' '+sort)
        # Cross-instance Redis cache uses shared DB/index generation.
        other=SearchService(Catalog(engine),meili,redis.Redis.from_url("redis://127.0.0.1:16379/0"))
        check(other.retrieve("Vue",search_term_groups("Vue"))[1]["cached"], "second service instance shares Redis cache")
        process_env={**os.environ,"SEARCH_TEST_DATABASE_URL":engine.url.render_as_string(hide_password=False),"SEARCH_TEST_INDEX":index,"PYTHONIOENCODING":"utf-8"}
        process_code="import sys,os,json; sys.path[:0]=['backend','.']; from sqlalchemy import create_engine; import redis; from search_catalog import Catalog; from search_service import SearchService,Meili; from v1_routes import search_term_groups; s=SearchService(Catalog(create_engine(os.environ['SEARCH_TEST_DATABASE_URL'])),Meili('http://127.0.0.1:17700',index=os.environ['SEARCH_TEST_INDEX']),redis.Redis(port=16379)); print(json.dumps(s.retrieve('Vue',search_term_groups('Vue'))[1]))"
        process=subprocess.run([sys.executable,'-c',process_code],cwd=ROOT,env=process_env,capture_output=True,text=True,encoding='utf-8')
        check(process.returncode==0 and json.loads(process.stdout)['cached'],"separate Python process shares versioned Redis candidates")
        execute("UPDATE tags SET name='new_api_tag' WHERE id=2")
        check(query("new_api_tag")[0]==[2], "tag change is searchable via pending consistency overlay before sync")
        check(not query("new_api_tag")[1]["cached"], "pending index version never caches old index candidates")
        sync.once()
        check(query("new_api_tag")[0]==[2], "tag update reaches Meilisearch")
        execute("UPDATE websites SET enabled=0 WHERE id=2")
        check(2 not in query("接口")[0], "unpublish hidden immediately before index cleanup")
        sync.once()
        check(2 not in [r["id"] for r in meili.documents()], "unpublished document deleted after sync")
        # A late wake-up event cannot re-publish an old payload.
        execute("INSERT INTO outbox_events(event_uid,aggregate_type,aggregate_uid,event_type,payload_json,status,attempt_count,max_attempts,available_at,created_at,updated_at) VALUES(UUID(),'search_catalog','public','search.changed',JSON_OBJECT('id',2,'enabled',1),'pending',0,5,UTC_TIMESTAMP(),UTC_TIMESTAMP(),UTC_TIMESTAMP())")
        sync.once()
        check(2 not in [r["id"] for r in meili.documents()], "late old payload cannot resurrect an unpublished document")
        saved=service.meili
        service.meili=Meili("http://127.0.0.1:1",index=index,timeout=.1)
        service.redis=None
        check(query("Vue")[1]["source"]=="database", "Meilisearch connection outage falls back to DB")
        service.meili=Meili("http://127.0.0.1:17700",index="stage2_test_missing")
        try:
            query("Vue")
            raise AssertionError("missing index silently hidden")
        except SearchConfigurationError:
            check(True, "missing index/configuration errors remain explicit")
        service.meili=saved; service.redis=redis.Redis(host="127.0.0.1",port=1,socket_connect_timeout=.1)
        check(query("Vue")[0][0]==3, "Redis outage allows uncached search")
        service.redis=cache
        def increment():
            execute("UPDATE websites SET summary='rebuild_increment',description='rebuild_increment' WHERE id=1")
            execute("INSERT INTO websites(id,name,url,summary,status,enabled,category_id) VALUES(9,'Increment','https://fixture.invalid/Increment','rebuild_increment','approved',1,1)")
        rebuilt=sync.rebuild(during_build=increment)
        check(set(query("rebuild_increment")[0])=={1,9}, "rebuild includes changed and newly inserted documents during initial build")
        sync.once()
        check(not any(sync.reconcile()[k] for k in ("missing","stale","not_public_or_removed")), "post-rebuild DB/index reconciliation is clean")
        # Lease recovery and failure retry using the same persistent outbox.
        execute("UPDATE websites SET summary='restart_case' WHERE id=3")
        execute("UPDATE outbox_events SET status='leased',worker_id='crashed',leased_until=UTC_TIMESTAMP()-INTERVAL 1 SECOND WHERE status='pending'")
        restarted=Sync(catalog,meili); restarted.once()
        execute("UPDATE outbox_events SET available_at=UTC_TIMESTAMP() WHERE status='pending'")
        check(restarted.once()["processed"]>0, "worker restart reclaims expired lease and retries current data")
        execute("UPDATE websites SET summary='failure_case' WHERE id=3")
        failing=Sync(catalog,Meili("http://127.0.0.1:1",index=index,timeout=.1))
        for _ in range(5):
            try: failing.once()
            except SearchUnavailable: pass
            execute("UPDATE outbox_events SET available_at=UTC_TIMESTAMP() WHERE status='pending'")
        with engine.connect() as conn:
            dead=conn.execute(text("SELECT COUNT(*) FROM outbox_events WHERE status='dead' AND last_error IS NOT NULL")).scalar()
        check(dead>0,"bounded retries preserve dead events and failure reason")
        check(sync.retry()["retried"]>0 and sync.once()["processed"]>0,"manual retry restores dead events without rewriting business data")
        check(not any(sync.reconcile()[k] for k in ("missing","stale","not_public_or_removed")), "final DB/index reconciliation clean")
        # Actual asynchronous task timeout: durable task UID survives a new worker.
        original_wait=meili.wait
        calls=[0]
        def timeout_once(uid,seconds=30):
            calls[0]+=1
            if calls[0]==1:
                raise SearchUnavailable("meili_task_timeout")
            return original_wait(uid,seconds)
        meili.wait=timeout_once
        try:
            with sync.lock():
                sync.task("PATCH",f"/indexes/{index}/settings",{"sortableAttributes":["id"]},target=index)
        except SearchUnavailable:
            pass
        check(sync.state()["task_id"] is not None,"timeout retains durable task ID without marking sync done")
        meili.wait=original_wait
        resumed=Sync(catalog,meili)
        with resumed.lock():
            resumed.resume()
        check(resumed.state()["task_id"] is None,"new worker confirms persisted task before further submissions")
        # Ambiguous submission fence cannot silently resubmit an index swap.
        sync.save(task_id=-1,task_kind="swap")
        try:
            with sync.lock(): sync.resume()
            raise AssertionError("ambiguous task not fenced")
        except SearchUnavailable:
            check(True,"ambiguous submission blocks subsequent writes")
        sync.recover()
        sync.rebuild()
        check(not any(sync.reconcile()[k] for k in ("missing","stale","not_public_or_removed")),"explicit recovery and fresh rebuild restore exact current catalog")
        # A commit immediately before swap remains in outbox and causes an overlay.
        real_task=sync.task
        def racing_task(method,path,body,**kw):
            if path=="/swap-indexes":
                execute("UPDATE websites SET enabled=0 WHERE id=9")
            return real_task(method,path,body,**kw)
        sync.task=racing_task
        sync.rebuild()
        check(9 not in query("Increment")[0],"commit at swap boundary hidden immediately by current DB validation")
        sync.task=real_task
        check(sync.once()["processed"]>0,"commit at swap boundary remains queued for incremental processing")
        check(9 not in [r["id"] for r in meili.documents()],"post-swap increment is not lost")
        try:
            with sync.lock():
                sync.task("PUT",f"/indexes/{index}/documents",[{"id":"invalid primary key with spaces"}],target=index)
            raise AssertionError("failed Meili task treated as successful")
        except SearchConfigurationError:
            check(sync.state()["indexed_revision"]==-1,"actual failed async task cannot advance indexed revision")
        sync.rebuild()
        # Reconciliation detects missing, stale and nonpublic documents independently.
        docs={r['id']:r for r in meili.documents()}
        stale={**docs[1],'summary':'stale corruption','fingerprint':'stale'}
        meili.wait(meili.request('PUT',f'/indexes/{index}/documents',[stale,{'id':6,'name':'Pending Paper','status':'pending'}])['taskUid'])
        meili.wait(meili.request('POST',f'/indexes/{index}/documents/delete-batch',[3])['taskUid'])
        diff=sync.reconcile()
        check(1 in diff['stale'] and 3 in diff['missing'] and 6 in diff['not_public_or_removed'],'reconcile distinguishes stale, missing and nonpublic documents')
        check(6 not in query('Paper')[0],'unreviewed stray indexed document is filtered by current DB')
        execute("UPDATE websites SET summary=summary WHERE id=1")
        sync.once()
        execute("DELETE FROM websites WHERE id=7")
        check(7 not in query('Paper')[0],'physical deletion hidden before index synchronization')
        sync.once()
        check(7 not in [r['id'] for r in meili.documents()],'physical deletion cleans index idempotently')
        # Migration rollback removes capture only, retaining resources and audit.
        with engine.connect() as conn:
            current=preview(conn)
            count_before=conn.execute(text("SELECT COUNT(*) FROM websites")).scalar()
            events_before=conn.execute(text("SELECT COUNT(*) FROM outbox_events")).scalar()
            for sql in current["rollback"]: conn.exec_driver_sql(sql)
            conn.commit()
            check(conn.execute(text("SELECT COUNT(*) FROM websites")).scalar()==count_before and conn.execute(text("SELECT COUNT(*) FROM outbox_events")).scalar()==events_before,"migration rollback retains all resources and outbox history")
            apply(conn,preview(conn))
        check(True,"capture migration can be re-applied after rollback")
        env={**os.environ,"SEARCH_TEST_DATABASE_URL":engine.url.render_as_string(hide_password=False),
             "SEARCH_TEST_INDEX":index,"MEILI_HOST":"http://127.0.0.1:17700","MEILI_MASTER_KEY":"","PYTHONIOENCODING":"utf-8"}
        def cli(command,filename,reviewed=None):
            args=[sys.executable,str(ROOT/'backend/scripts/search_sync.py'),command,'--test-database','--output',str(artifact/filename)]
            if reviewed: args+=['--preview',str(artifact/reviewed)]
            run=subprocess.run(args,env=env,capture_output=True,text=True,encoding='utf-8')
            if run.returncode: raise AssertionError('CLI failed: '+command+' '+run.stderr[-2000:])
            return json.loads((artifact/filename).read_text(encoding='utf-8'))
        cli('migration-preview','cli-preview.json')
        check(cli('migration-apply','cli-apply.json','cli-preview.json')['applied'],'CLI requires and accepts matching migration preview')
        cli('migration-rollback-preview','cli-rollback-preview.json')
        check(cli('migration-rollback','cli-rollback.json','cli-rollback-preview.json')['applied'],'CLI reviewed rollback succeeds without deleting resources')
        cli('migration-preview','cli-reapply-preview.json')
        cli('migration-apply','cli-reapply.json','cli-reapply-preview.json')
        cli('status','cli-status.json')
        check(not any(cli('reconcile','cli-reconcile.json')[k] for k in ('missing','stale','not_public_or_removed')),'CLI status and reconciliation work against retained test database')
        check(sync.state()['indexed_revision']==-1 and cli('rebuild','final-rebuild.json')['swapped'],'Rollback invalidates cache generation; CLI reapply and safe rebuild restore indexed state')
        report.update(status="passed",retained_previous_index=rebuilt["retained_previous_index"])
    except Exception as exc:
        report.update(status="failed",failure=type(exc).__name__+": "+str(exc))
        raise
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
        print(json.dumps({"database":database,"status":report.get("status"),"checks":len(report["checks"])}))


if __name__=="__main__":
    main()
