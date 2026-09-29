"""Opt-in post-ranking; frozen phase1 scores are never modified."""
from datetime import datetime, timedelta
import json
import os
from urllib.parse import urlsplit

VERSION='diversity-v1'
MIGRATION='20260926_feedback_v1'
REASONS={'irrelevant','known','later'}

def enabled(app,key):
    return str(app.config.get(key,os.getenv(key,'0'))).lower() in {'1','true'}

def days(app,key,default):
    return max(1,min(365,int(app.config.get(key,os.getenv(key,str(default))))))

def active(row,now):
    return bool(row.get('reason')) and (row.get('expires_at') is None or row['expires_at']>now)

def signals(site):
    tags=site.get('tags') or []
    if isinstance(tags,str): tags=[tags]
    result={('task',str(t)) for t in tags if isinstance(t,(str,int)) and t}
    if site.get('category_id') is not None:result.add(('type',str(site['category_id'])))
    host=urlsplit(site.get('url') or '').hostname
    if host:result.add(('source',host))
    return result

def reorder(candidates,preferences=(),*,now=None,diversity=False,band=5):
    """Only caller-confirmed public candidates; deterministic local score bands."""
    now=now or datetime.utcnow()
    prefs={r['website_id']:r for r in preferences if active(r,now)}
    pool=[]; seen=set()
    for position,original in enumerate(candidates):
        site=dict(original)
        if site.get('status')!='approved' or not site.get('enabled',1): continue
        if float(site.get('match_score') or 0)<=0: continue
        if not site.get('match_evidence') and not any(float(site.get(k) or 0)>0 for k in ('need_score','direction_score','other_tags_score')): continue
        if site.get('hard_constraints_met') is False or site.get('match_status') in {'partial','unverified'}: continue
        if any(c.get('strength')=='must' and c.get('state')!='met' for c in site.get('condition_checks',[])): continue
        pref=prefs.get(site['id'],{})
        if pref.get('reason') in {'irrelevant','later'}: continue
        # Only committed identity links supply this value. Names/hosts are not identities.
        product=site.get('canonical_site_id',site['id'])
        if diversity and product in seen: continue
        seen.add(product)
        site.update(baseline_position=position+1,rerank_reason=[],rerank_version=f'{VERSION}.b{band:g}' if diversity else 'baseline')
        site['_known']=pref.get('reason')=='known'
        pool.append(site)
    output=[]; coverage=set()
    # Preserve baseline order except within score-near contiguous bands.
    while pool:
        anchor=float(pool[0].get('match_score') or 0)
        count=1
        while count<len(pool) and abs(float(pool[count].get('match_score') or 0)-anchor)<=band: count+=1
        group,pool=pool[:count],pool[count:]
        while group:
            chosen=min(group,key=lambda s:(s['_known'], -len(signals(s)-coverage) if diversity else 0,s['baseline_position'],int(s['id'])))
            group.remove(chosen)
            if chosen['_known']: chosen['rerank_reason'].append('已知资源在相关性相近结果中后置')
            if diversity and len(signals(chosen)-coverage): chosen['rerank_reason'].append('增加已记录标签、类别或来源覆盖')
            coverage.update(signals(chosen));chosen.pop('_known')
            chosen['rerank_position']=len(output)+1;output.append(chosen)
    return output


class Conflict(ValueError): pass

class Preferences:
    def __init__(self,connection_factory):self.connect=connection_factory

    def ready(self,cursor):
        cursor.execute('SELECT active FROM recommendation_feedback_migrations WHERE version=%s',(MIGRATION,))
        if not (cursor.fetchone() or {}).get('active'): raise RuntimeError('feedback migration inactive')

    def list(self,user_id):
        conn=self.connect()
        try:
            with conn.cursor() as c:
                self.ready(c)
                c.execute('SELECT p.*,w.name FROM recommendation_preferences p LEFT JOIN websites w ON w.id=p.website_id WHERE p.user_id=%s ORDER BY p.website_id',(user_id,))
                return list(c.fetchall())
        finally:conn.close()

    def change(self,user_id,payload,*,later_days=30,known_days=7,now=None):
        now=now or datetime.utcnow()
        if not isinstance(payload,dict) or not {'website_id','reason','expected_revision','request_id'}<=set(payload) or set(payload)-{'website_id','reason','expected_revision','request_id','recommendation_batch_id','algorithm_version','rerank_version'}:raise ValueError('invalid fields')
        sid=payload.get('website_id');reason=payload.get('reason');revision=payload.get('expected_revision');key=payload.get('request_id')
        if type(sid) is not int or not 0<sid<2147483648 or type(revision) is not int or not 0<=revision<9223372036854775807 or (reason is not None and (not isinstance(reason,str) or reason not in REASONS)):raise ValueError('invalid feedback')
        if not isinstance(key,str) or not 8<=len(key)<=64 or not all(x.isalnum() or x in '-_' for x in key):raise ValueError('invalid request_id')
        for field in ('recommendation_batch_id','algorithm_version','rerank_version'):
            if field in payload and (not isinstance(payload[field],str) or len(payload[field])>128):raise ValueError('invalid context')
        fingerprint=json.dumps(payload,sort_keys=True,separators=(',',':'))
        conn=self.connect()
        try:
            conn.begin()
            with conn.cursor() as c:
                self.ready(c)
                c.execute('SELECT id FROM users WHERE id=%s FOR UPDATE',(user_id,))
                if not c.fetchone():raise ValueError('unknown user')
                c.execute('SELECT fingerprint,result_json FROM recommendation_feedback_operations WHERE user_id=%s AND request_id=%s FOR UPDATE',(user_id,key))
                operation=c.fetchone()
                if operation:
                    if operation['fingerprint']!=fingerprint:raise Conflict('request id reused')
                    conn.rollback();return json.loads(operation['result_json'])
                c.execute('SELECT * FROM recommendation_preferences WHERE user_id=%s AND website_id=%s FOR UPDATE',(user_id,sid))
                old=c.fetchone() or {'revision':0,'reason':None}
                if old['revision']!=revision:raise Conflict('preference changed; refresh first')
                c.execute('SELECT id FROM websites WHERE id=%s',(sid,))
                if not c.fetchone():raise ValueError('unknown resource')
                expires=now+timedelta(days=later_days if reason=='later' else known_days) if reason in {'later','known'} else None
                # Repeated equivalent submissions are no-ops, not extensions of suspension.
                if old['reason']==reason and (reason is None or active(old,now)):
                    result={'website_id':sid,'revision':revision,'reason':reason,'expires_at':old.get('expires_at').isoformat() if old.get('expires_at') else None}
                else:
                    result={'website_id':sid,'revision':revision+1,'reason':reason,'expires_at':expires.isoformat() if expires else None}
                    c.execute('INSERT INTO recommendation_preferences(user_id,website_id,reason,revision,expires_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE reason=VALUES(reason),revision=VALUES(revision),expires_at=VALUES(expires_at),updated_at=VALUES(updated_at)',(user_id,sid,reason,revision+1,expires,now))
                    batch=payload.get('recommendation_batch_id')
                    if reason is None and not batch:
                        c.execute("SELECT recommendation_batch_id FROM user_behavior_events WHERE user_id=%s AND website_id=%s AND event_type='feedback' ORDER BY id DESC LIMIT 1",(user_id,sid))
                        batch=(c.fetchone() or {}).get('recommendation_batch_id')
                    metadata={'event_version':'feedback-v1','feedback_reason':reason or old['reason'],'preference_revision':revision+1,'expires_at':result['expires_at'],'algorithm_version':payload.get('algorithm_version','phase1-v1'),'rerank_version':payload.get('rerank_version','baseline'),'request_id':key}
                    c.execute('INSERT INTO user_behavior_events(user_id,website_id,event_type,source,recommendation_batch_id,metadata_json,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s)',(user_id,sid,'feedback' if reason else 'feedback_undo','personalized_recommendation',batch,json.dumps(metadata),now))
                c.execute('INSERT INTO recommendation_feedback_operations(user_id,request_id,fingerprint,result_json) VALUES(%s,%s,%s,%s)',(user_id,key,fingerprint,json.dumps(result)))
            conn.commit();return result
        except Exception:
            conn.rollback();raise
        finally:conn.close()
