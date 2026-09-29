"""Opt-in real provider validation over an EXISTING isolated stage-3 catalog.

No source DB writes, no simulated model, no credential or response-body logging.
Create a fixture with verify_ai_retrieval_stage3.py first; use its database name.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from dotenv import load_dotenv
from ai_retrieval import configured_model, retrieve_recommendations, evaluate

QUERY='免费、中文、无需安装、适合新手的论文绘图工具'
CASES=[('multi',QUERY,''),('negative','不要付费，不需要中文也可以的接口调试工具',''),
       ('conflict','免费但必须付费的论文绘图工具',''),('profile_conflict',QUERY,'程序员'),
       ('unknown','免费、中文、无需安装的论文绘图工具','')]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',help='Explicitly allow up to ten real model calls')
    parser.add_argument('--database',required=True,help='Existing ai_retrieval_<12 hex>_test fixture only')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/recommendation/stage3-real-model-verification.json')
    args=parser.parse_args(argv)
    if not re.fullmatch(r'ai_retrieval_[0-9a-f]{12}_test',args.database): parser.error('isolated stage-3 database required')
    load_dotenv(ROOT/'backend/.env',override=False)
    report={'captured_at':datetime.now(timezone.utc).isoformat(),'database':args.database,
            'provider':'existing DeepSeek client','real_model_executed':False,'cases':[],
            'retrieval':'shared SearchService, explicit database mode, read-only isolated fixture'}
    reason= 'run_flag_required' if not args.run else 'model_disabled' if os.getenv('AI_REQUIREMENTS_MODEL_ENABLED','1')!='1' else 'missing_credentials' if not os.getenv('DEEPSEEK_API_KEY') else None
    if reason:
        report.update(status='not_executed',reason=reason)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('真实联调未执行：'+reason)
        return 0
    # No application import/startup or migration; Catalog explicitly opens read-only snapshots.
    from db_pool import validate_database_config
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL
    from search_catalog import Catalog
    from search_service import SearchService
    cfg=validate_database_config()
    if cfg['host'] not in ('localhost','127.0.0.1','::1'): raise ValueError('local isolated database only')
    engine=create_engine(URL.create('mysql+pymysql',username=cfg['user'],password=cfg['password'],host=cfg['host'],port=cfg['port'],database=args.database))
    try:
        service=SearchService(Catalog(engine))
        rows={r['id']:r for r in service.catalog.snapshot()[2]}
        if len(rows)!=8 or rows[1]['name']!='Plot Alpha' or rows[3]['name']!='Plot Unknown' or not all(r['url'].startswith('https://fixture.invalid/products/') for r in rows.values()):
            raise ValueError('fixture mismatch')
        for name,query,occupation in CASES:
            entry={'case':name,'model_calls':0};start=time.perf_counter()
            provider=configured_model()
            def real_call(prompt,payload):
                entry['model_calls']+=1
                report['real_model_executed']=True
                return provider(prompt,payload)
            try:
                result=retrieve_recommendations(query,service,occupation=occupation,model=real_call)
                assert result['requirements']['source']=='model','parser fell back'
                assert not result['degraded'],'provider or explanation fell back'
                assert all(c['evidence'] in query for c in result['requirements']['conditions'])
                assert 1<=entry['model_calls']<=2
                for match in result['matches']:
                    current=rows[match['site']['id']]
                    assert (match['site']['name'],match['site']['url'])==(current['name'],current['url'])
                    status,checks=evaluate(current,result['requirements'])
                    assert match['status']==status and match['checks']==checks
                    assert any(c['field']=='task' and c['state']=='met' and c['evidence'] for c in checks)
                if name=='conflict': assert result['clarifications'] and not result['matches']
                elif name=='unknown': assert any(m['site']['id']==3 and m['status']=='unverified' for m in result['matches'])
                elif name=='negative': assert result['matches'][0]['site']['id']==4 and result['matches'][0]['status']=='full'
                else: assert result['matches'][0]['site']['id']==1 and result['matches'][0]['status']=='full'
                entry.update(status='passed',conditions=result['requirements']['conditions'],
                             resource_ids=[m['site']['id'] for m in result['matches']])
            except Exception as exc:
                entry.update(status='failed',failure_type=type(exc).__name__)
            entry['duration_ms']=round((time.perf_counter()-start)*1000,3);report['cases'].append(entry)
        report['status']='passed' if all(c['status']=='passed' for c in report['cases']) else 'failed'
    except Exception as exc:
        report.update(status='failed',failure_type=type(exc).__name__)
    finally:
        engine.dispose()
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'real_model_executed':report['real_model_executed'],
                      'passed':sum(c['status']=='passed' for c in report['cases']),'cases':len(report['cases'])}))
    return int(report['status']!='passed')


if __name__=='__main__':raise SystemExit(main())
