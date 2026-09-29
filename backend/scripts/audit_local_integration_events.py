"""Read-only audit of this rehearsal's synthetic browser events, never real data."""
import json, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from db_pool import validate_database_config
import pymysql

def main():
    database = json.loads((ROOT/'docs/release/resource-chain.json').read_text())['test_database']
    import re
    if not re.fullmatch(r'resource_chain_[a-f0-9]{12}_test', database):
        raise ValueError('isolated manifest required')
    cfg = validate_database_config()
    if cfg['host'] not in ('127.0.0.1','localhost'): raise ValueError('local only')
    with pymysql.connect(**{**cfg,'database':database},cursorclass=pymysql.cursors.DictCursor) as conn, conn.cursor() as c:
        c.execute('START TRANSACTION READ ONLY')
        c.execute('SELECT * FROM user_behavior_events ORDER BY id')
        rows=c.fetchall()
        c.execute('SELECT user_id,website_id,reason,revision,expires_at FROM recommendation_preferences')
        preferences=c.fetchall()
        c.execute('SELECT NOW() AS database_now,UTC_TIMESTAMP() AS utc_now,@@session.time_zone AS session_timezone')
        clock=c.fetchone()
        conn.rollback()
    for r in rows: r['metadata']=json.loads(r['metadata_json'] or '{}')
    visible=[r for r in rows if r['metadata'].get('event_version')=='visible-v2']
    impressions=[r for r in visible if r['event_type']=='impression']
    clicks=[r for r in visible if r['event_type']=='click']
    key=lambda r:(r['user_id'],r['website_id'],r['recommendation_batch_id'],r['session_id'])
    counts=Counter(key(r) for r in impressions)
    paired=lambda click:any(key(r)==key(click) and r['created_at']<=click['created_at'] and r['metadata'].get('position')==click['metadata'].get('position') for r in impressions)
    result={
      'captured_at_utc':datetime.now(timezone.utc).isoformat(),'database':database,'clock':clock,
      'source':'real browser operations against isolated Flask; includes pre-fix clicks as legacy, never production evidence',
      'counts':dict(Counter(r['event_type'] for r in rows)),
      'visible_v2_by_account':dict(Counter(r['user_id'] for r in impressions)),
      'visible_v2_missing_time':sum(r['created_at'] is None for r in visible),
      'visible_v2_missing_position':sum(not str(r['metadata'].get('position','')).isdigit() for r in impressions+clicks),
      'duplicate_visible_impressions':sum(n-1 for n in counts.values()),
      'visible_clicks':len(clicks),'visible_clicks_linked_to_prior_same_account_batch_position':sum(paired(r) for r in clicks),
      'visible_clicks_with_same_account_batch_position_exposure':sum(any(key(r)==key(click) and r['metadata'].get('position')==click['metadata'].get('position') for r in impressions) for click in clicks),
      'test_exclusions':[1,2,3,4],'events_after_explicit_test_exclusion':sum(r['user_id'] not in (1,2,3,4) for r in rows),
      'offscreen_batch_impressions':sum(r['recommendation_batch_id']=='rec_20e0673f8a874cdaab4df58305565be9:graduate_student:0:size-8' for r in impressions),
      'preferences':preferences,
      'recent_visible_click_evidence':[{'user_id':r['user_id'],'website_id':r['website_id'],'batch':r['recommendation_batch_id'],'created_at':r['created_at'],'metadata':r['metadata']} for r in clicks[-3:]],
      'limits':['no historical event backfill','background-tab and slow network races require separate browser evidence','counts are test operations, not recommendation effectiveness']}
    path=ROOT/'docs/release/browser-events.json'
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('recent_visible_click_evidence','preferences','limits')},ensure_ascii=False,default=str))
if __name__=='__main__':main()
