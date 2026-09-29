import json,sys,time,statistics
from datetime import datetime,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from recommendation_stage4 import reorder
from recommend_service import rank_sites
from stage4_fixtures import resources,PROFILES,TASKS,TYPES

def run():
    rows=resources();now=datetime(2026,9,26);report={'sample_resources':len(rows),'profiles':2,'top_k':3,'model_calls':0,'conditions':'fixed memory fixtures, no DB/Redis/network; 20 warm in-process timing samples','comparisons':[]}
    # Same public/hard-condition eligibility for the frozen baseline and new policy.
    eligible=[r for r in rows if r['enabled'] and r['hard_constraints_met']]
    def metrics(items,case):
        top=items[:3];ids=[s['id'] for s in top];products=[case['product_ids'].get(i,i) for i in ids]
        return {'ids':ids,'precision_at_3':sum(i in case['relevant_ids'] for i in ids)/len(ids) if ids else 0,
            'confirmed_duplicate_rate':(len(products)-len(set(products)))/len(products) if products else 0,
            'task_coverage':len(set().union(*(TASKS.get(i,set()) for i in ids))),
            'tool_type_coverage':len({TYPES[i] for i in ids if i in TYPES}),
            'must_violations':sum(not s['hard_constraints_met'] for s in top),
            'reason_evidence_valid':all(s.get('match_evidence') and all(e['value'] in s.get(e['resource_field'],[]) if isinstance(s.get(e['resource_field']),list) else str(e['value']).casefold() in str(s.get(e['resource_field'],'')).casefold() for e in s['match_evidence']) for s in top)}
    for case in PROFILES:
        baseline=rank_sites(eligible,case['profile'],60);new=reorder(baseline,now=now,diversity=True)
        before,after=metrics(baseline,case),metrics(new,case)
        assert after['precision_at_3']>=before['precision_at_3']==1
        assert after['confirmed_duplicate_rate']==0 and after['task_coverage']>=before['task_coverage'] and after['tool_type_coverage']>=before['tool_type_coverage']
        assert after['must_violations']==0 and after['reason_evidence_valid']
        assert all(s['match_score']==next(r['match_score'] for r in baseline if r['id']==s['id']) for s in new)
        sid=new[0]['id'];irrelevant=[{'website_id':sid,'reason':'irrelevant','expires_at':None}]
        assert sid not in [r['id'] for r in reorder(baseline,irrelevant,now=now,diversity=True)]
        assert sid in [r['id'] for r in reorder(baseline,[],now=now,diversity=True)]
        later=[{'website_id':sid,'reason':'later','expires_at':now+timedelta(days=30)}]
        assert sid not in [r['id'] for r in reorder(baseline,later,now=now,diversity=True)]
        assert sid in [r['id'] for r in reorder(baseline,later,now=now+timedelta(days=31),diversity=True)]
        known=[{'website_id':sid,'reason':'known','expires_at':now+timedelta(days=7)}]
        demoted=reorder(baseline,known,now=now,diversity=True)
        assert next(i for i,r in enumerate(demoted) if r['id']==sid)>0
        timing=[];baseline_timing=[]
        for _ in range(20):
            start=time.perf_counter();rank_sites(eligible,case['profile'],60);baseline_timing.append((time.perf_counter()-start)*1000)
            start=time.perf_counter();again=reorder(baseline,now=now,diversity=True);timing.append((time.perf_counter()-start)*1000)
            assert [r['id'] for r in again]==[r['id'] for r in new]
        report['comparisons'].append({'profile':case['name'],'baseline':before,'diversity':after,'baseline_median_ms':statistics.median(baseline_timing),'additional_rerank_median_ms':statistics.median(timing),'stable':True,'feedback_undo_expiry_known':True})
    report['status']='passed';return report

if __name__=='__main__':
    report=run();(ROOT/'docs/recommendation/stage4-offline-evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
