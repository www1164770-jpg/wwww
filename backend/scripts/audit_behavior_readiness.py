"""Print only aggregate evidence; never start Flask or migrate a database."""
import argparse,json,os,re,sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from db_pool import validate_database_config
from behavior_readiness import audit_connection
import pymysql

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--test-accounts-reviewed',action='store_true',help='Only after the explicit exclusion list has been manually verified, including an intentionally empty list')
    a=p.parse_args();result={'captured_at_utc':datetime.now(timezone.utc).isoformat()}
    try:
        cfg=validate_database_config()
        if re.search(r'(_test$|^test_)',cfg['database']): raise ValueError('isolated_database_not_real_evidence')
        result['source']={k:cfg[k] for k in ('host','port','database')}
        result['configured_flags']={k:os.getenv(k,'unset') for k in ('SEARCH_BACKEND','SEARCH_SYNC_ENABLED','RECOMMENDATION_RERANK_ENABLED','RECOMMENDATION_FEEDBACK_ENABLED','RECOMMENDATION_EXPOSURE_V2')}
        result['real_model_key_present']=bool(os.getenv('DEEPSEEK_API_KEY'))
        raw=os.getenv('RECOMMENDATION_METRICS_TEST_USER_IDS','')
        if raw and not re.fullmatch(r'\s*\d+(\s*,\s*\d+)*\s*',raw): raise ValueError('invalid_test_user_ids')
        ids=[int(v) for v in raw.split(',') if v.strip()]
        with pymysql.connect(**cfg,cursorclass=pymysql.cursors.DictCursor) as conn:
            result.update(audit_connection(conn,excluded=ids,exclusions_verified=a.test_accounts_reviewed))
    except Exception as exc:
        result.update(status='cannot_evaluate',failure_type=type(exc).__name__,failure_code=exc.args[0] if exc.args and isinstance(exc.args[0],int) else None)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'output':str(a.output)}))
if __name__=='__main__':main()
