"""Small, phased restart rehearsal on the manifest's existing synthetic DB."""
import argparse,json,sys,time
from pathlib import Path
import pymysql,requests
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from db_pool import validate_database_config

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['change','indexed','down','deleted','restore','finish']);a=p.parse_args()
    database=json.loads((ROOT/'docs/release/resource-chain.json').read_text())['test_database']
    assert database=='resource_chain_7a54fb93b0d4_test'
    cfg=validate_database_config();assert cfg['host'] in ('127.0.0.1','localhost')
    report_path=ROOT/'docs/release/sync-recovery.json'
    report=json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {'database':database,'checks':[]}
    marker='ReleaseSyncSep28';base='http://127.0.0.1:15000/api/sites/search'
    def search():
        r=requests.get(base,params={'q':marker},timeout=15);r.raise_for_status();return r.json()['data']
    def record(label,data):report['checks'].append({'label':label,'at':time.time(),'data':data})
    with pymysql.connect(**{**cfg,'database':database},cursorclass=pymysql.cursors.DictCursor) as conn,conn.cursor() as c:
        c.execute('SELECT DATABASE() d');assert c.fetchone()['d']==database
        if a.phase=='change':
            c.execute('SELECT summary,status FROM websites WHERE id=49');original=c.fetchone()
            if 'original' in report:assert report['original']==original,'restore existing rehearsal first'
            else:report['original']=original
            # Persist restoration evidence before committing a test mutation.
            report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            c.execute('UPDATE websites SET summary=%s WHERE id=49',(marker+' synthetic integration fixture',));conn.commit()
            data=search();assert 49 in [x['id'] for x in data['items']];assert data['retrieval']['source']=='meilisearch+pending_database' and not data['cached']
            record('worker stopped: committed update visible through pending-index fallback',data['retrieval'])
        elif a.phase=='indexed':
            for _ in range(60):
                data=search()
                if data['retrieval']['source']=='meilisearch':break
                time.sleep(.5)
            assert data['retrieval']['source']=='meilisearch' and 49 in [x['id'] for x in data['items']]
            record('restarted real worker confirms index task',data['retrieval'])
            warm=search();assert warm['cached'];record('redis warm version after index success',warm['retrieval'])
        elif a.phase=='down':
            c.execute("UPDATE websites SET status='pending' WHERE id=49");conn.commit()
            data=search();assert 49 not in [x['id'] for x in data['items']];record('unpublished resource immediately absent before worker catches up',data['retrieval'])
        elif a.phase=='deleted':
            url='http://127.0.0.1:17700/indexes/stage2_test_release_'+database+'/documents/49'
            for _ in range(60):
                response=requests.get(url,timeout=10)
                if response.status_code==404:break
                time.sleep(.5)
            assert response.status_code==404;record('actual index document deleted after worker restart',{'status':404})
        elif a.phase=='restore':
            c.execute('UPDATE websites SET summary=%s,status=%s WHERE id=49',(report['original']['summary'],report['original']['status']));conn.commit();record('synthetic resource restored',{'id':49})
        elif a.phase=='finish':
            for _ in range(60):
                data=search()
                if data['retrieval']['source']=='meilisearch':break
                time.sleep(.5)
            assert 49 not in [x['id'] for x in data['items']]
            c.execute('SELECT summary,status FROM websites WHERE id=49');assert c.fetchone()==report['original']
            c.execute("SELECT status,COUNT(*) n FROM outbox_events WHERE event_type='search.changed' GROUP BY status");states=c.fetchall()
            assert all(x['status']=='processed' for x in states);record('restored resource, drained outbox and no stale marker',{'outbox':states,'retrieval':data['retrieval']})
            report['status']='passed'
    report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'phase':a.phase,'checks':len(report['checks']),'status':report.get('status','in_progress')}))
if __name__=='__main__':main()

