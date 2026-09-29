"""Read-only evidence audit. No identity guesses and no historical backfill."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta

EVENTS = ('impression', 'click', 'favorite', 'repeat_visit', 'feedback', 'feedback_undo')

def analyze(rows, *, excluded=(), exclusions_verified=False, now=None, truncated=False):
    now = now or datetime.now()
    rows = [r for r in rows if r.get('user_id') not in set(excluded)]
    groups = defaultdict(list)
    quality = Counter()
    owners = defaultdict(set)
    for raw in rows:
        r = dict(raw)
        try:
            m = json.loads(r.get('metadata_json') or '{}')
            if not isinstance(m, dict): raise ValueError()
        except (ValueError, TypeError):
            m = {}; quality['invalid_metadata'] += 1
        r['meta'] = m
        key = (m.get('event_version') or 'legacy-v1', m.get('algorithm_version') or 'unknown', m.get('rerank_version') or 'baseline')
        groups[key].append(r)
        quality['missing_time'] += not isinstance(r.get('created_at'), datetime)
        quality['invalid_resource'] += not bool(r.get('valid_resource'))
        quality['invalid_user'] += not bool(r.get('valid_user'))
        quality['unknown_event_type'] += r.get('event_type') not in EVENTS
        quality['missing_batch'] += not bool(r.get('recommendation_batch_id'))
        quality['missing_position'] += not str(m.get('position', '')).isdigit()
        if r.get('recommendation_batch_id'): owners[r['recommendation_batch_id']].add(r.get('user_id'))
    partitions = []
    for versions, events in sorted(groups.items()):
        counts = Counter(r['event_type'] for r in events)
        impression_keys = Counter()
        click_keys = Counter()
        occupations = Counter(); profiles = Counter()
        times = []; impressions = []
        for r in events:
            t = r.get('created_at')
            if isinstance(t, datetime): times.append(t)
            k = (r.get('user_id'), r.get('website_id'), r.get('source'), r.get('recommendation_batch_id'), r.get('session_id'))
            if r['event_type'] == 'click' and isinstance(t, datetime): click_keys[k + (t,)] += 1
            if r['event_type'] == 'impression':
                impressions.append(r); impression_keys[k] += 1
                m = r['meta']
                if m.get('occupation') not in (None, '', 'unknown'): occupations[m['occupation']] += 1
                if all(m.get(f) not in (None, '', 'unknown') for f in ('direction', 'primary_need')):
                    profiles[(m['direction'], m['primary_need'])] += 1
        orphan = 0; temporal_unknown = 0
        for r in events:
            if r['event_type'] != 'click' or r.get('source') != 'personalized_recommendation': continue
            matches = [i for i in impressions if all(i.get(f) == r.get(f) for f in ('user_id','website_id','recommendation_batch_id','session_id')) and r.get('recommendation_batch_id')]
            if not matches: orphan += 1
            elif not isinstance(r.get('created_at'), datetime) or any(not isinstance(i.get('created_at'), datetime) for i in matches): temporal_unknown += 1
            elif not any(i['created_at'] <= r['created_at'] for i in matches): orphan += 1
        partitions.append({'versions': dict(zip(('event','algorithm','rerank'), versions)),
            'collection_versions': dict(Counter(r['meta'].get('collection_version') or 'unknown' for r in events)),
            'events': {e: counts[e] for e in EVENTS}, 'account_count_unverified': len({r['user_id'] for r in events if r.get('user_id')}),
            'batches': len({r['recommendation_batch_id'] for r in impressions if r.get('recommendation_batch_id')}),
            'duplicate_impressions': sum(n-1 for n in impression_keys.values()),
            'duplicate_clicks_same_timestamp': sum(n-1 for n in click_keys.values()),
            'click_duplicate_check_unknown': sum(r['event_type']=='click' and not isinstance(r.get('created_at'),datetime) for r in events),
            'orphan_recommendation_clicks': orphan, 'click_order_unknown': temporal_unknown,
            'historical_occupations': len(occupations) if sum(occupations.values())==len(impressions) and impressions else None,
            'historical_profiles': len(profiles) if sum(profiles.values())==len(impressions) and impressions else None,
            'qualifying_occupations': sum(n>=50 for n in occupations.values()), 'qualifying_profiles': sum(n>=50 for n in profiles.values()),
            'first_at': min(times).isoformat() if times else None, 'last_at': max(times).isoformat() if times else None,
            'windows': {str(days): ({e:sum(r['event_type']==e and now-timedelta(days=days)<=r['created_at']<=now for r in events) for e in EVENTS} if len(times)==len(events) else None) for days in (7,30)}})
    return {'audit_version':'readiness-audit-v1','status':'cannot_evaluate' if (not exclusions_verified or quality['missing_time'] or truncated or not rows) else 'requires_manual_review',
        'algorithm_experiment_enabled':False,'rows_after_exclusion':len(rows),'truncated':truncated,
        'test_account_exclusions_verified':exclusions_verified,'excluded_account_count':len(set(excluded)),
        'quality':dict(quality),'batch_ids_shared_by_accounts':sum(len(v)>1 for v in owners.values()),
        'cross_account_attribution':'shared batch IDs are a diagnostic, not proof; no server-issued historical batch ownership ledger',
        'display_proof':'client context only; historical position/visibility cannot be reconstructed from current profile',
        'partitions':partitions}

def audit_connection(conn, *, excluded=(), exclusions_verified=False, limit=100000):
    with conn.cursor() as c:
        c.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY')
        try:
            c.execute('SELECT NOW() AS database_now, UTC_TIMESTAMP() AS utc_now, @@session.time_zone AS session_timezone, TIMESTAMPDIFF(MINUTE,UTC_TIMESTAMP(),NOW()) AS utc_offset_minutes')
            clock = c.fetchone()
            c.execute('SHOW TABLES'); tables = {next(iter(r.values())) for r in c.fetchall()}
            state = {t:t in tables for t in ('user_behavior_events','search_sync_state','outbox_events','recommendation_feedback_migrations','resource_identity_links')}
            if 'user_behavior_events' not in tables:
                return {'status':'cannot_evaluate','reason':'event_table_missing','runtime_tables':state,'database_clock':clock}
            c.execute('SHOW COLUMNS FROM user_behavior_events'); schema = c.fetchall()
            c.execute('SELECT e.*, (w.id IS NOT NULL) AS valid_resource,(u.id IS NOT NULL) AS valid_user FROM user_behavior_events e LEFT JOIN websites w ON w.id=e.website_id LEFT JOIN users u ON u.id=e.user_id ORDER BY e.id LIMIT %s',(limit+1,))
            rows = c.fetchall()
            result = analyze(rows[:limit],excluded=excluded,exclusions_verified=exclusions_verified,now=clock['database_now'],truncated=len(rows)>limit)
            result.update(database_clock=clock,runtime_tables=state,created_at_schema=next((r for r in schema if r['Field']=='created_at'),None),window='all stored rows; 7/30 day windows only when timestamps are complete')
            return result
        finally:
            conn.rollback()
