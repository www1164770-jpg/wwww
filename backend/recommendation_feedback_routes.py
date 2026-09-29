"""Feedback API uses existing authentication and seven-field response helpers."""
from flask import request
from flask_jwt_extended import jwt_required
import os
from recommendation_stage4 import Preferences,Conflict,enabled,days,reorder

def register(app,connect,current_user,success,error,catalog=None):
    prefs=Preferences(connect)
    @app.get('/api/recommendation/preferences')
    @jwt_required()
    def preferences_list():
        user=current_user()
        if not user:return error('user not found',404,404)
        if not enabled(app,'RECOMMENDATION_FEEDBACK_ENABLED'):return success({'enabled':False,'items':[]})
        try:
            rows=prefs.list(user['id'])
            for row in rows:
                for field in ('expires_at','updated_at'):
                    row[field]=row[field].isoformat()+'Z' if row.get(field) else None
                row.pop('user_id',None)
            return success({'enabled':True,'items':rows,'later_days':days(app,'RECOMMENDATION_LATER_DAYS',30),'known_days':days(app,'RECOMMENDATION_KNOWN_DAYS',7)})
        except Exception:return error('推荐偏好暂不可用',503,503)

    @app.post('/api/recommendation/preferences')
    @jwt_required()
    def preferences_change():
        user=current_user()
        if not user:return error('user not found',404,404)
        if not enabled(app,'RECOMMENDATION_FEEDBACK_ENABLED'):return error('推荐反馈尚未启用',503,503)
        try:
            result=prefs.change(user['id'],request.get_json(silent=True),later_days=days(app,'RECOMMENDATION_LATER_DAYS',30),known_days=days(app,'RECOMMENDATION_KNOWN_DAYS',7))
            if result['expires_at']:result={**result,'expires_at':result['expires_at']+'Z'}
            return success(result)
        except Conflict:return error('偏好已发生变化，请刷新后重试',409,409)
        except ValueError:return error('反馈参数无效',400,400)
        except Exception:return error('反馈未保存，请重试',503,503)

    def decorate(sites,user_id=None):
        feedback=enabled(app,'RECOMMENDATION_FEEDBACK_ENABLED')
        diversity=enabled(app,'RECOMMENDATION_RERANK_ENABLED')
        exposure=enabled(app,'RECOMMENDATION_EXPOSURE_V2')
        if not (feedback or diversity or exposure):return sites
        if catalog is None:raise RuntimeError('stage4 requires shared catalog')
        current={s['id']:s for s in catalog.snapshot()[2]}
        rows=[{**current[s['id']],**s,'status':current[s['id']].get('status'),'enabled':current[s['id']].get('enabled',1),
               'canonical_site_id':current[s['id']].get('canonical_site_id',s['id'])} for s in sites if s['id'] in current]
        preferences=prefs.list(user_id) if feedback and user_id else []
        band=float(app.config.get('RECOMMENDATION_DIVERSITY_BAND',os.getenv('RECOMMENDATION_DIVERSITY_BAND','5')))
        if not 0<=band<=10:raise ValueError('diversity score band must be between 0 and 10')
        if feedback or diversity:rows=reorder(rows,preferences,diversity=diversity,band=band)
        for row in rows:
            row['recommendation_policy_version']='stage4-v1'
            row['feedback_enabled']=bool(feedback and user_id)
            row['event_version']='visible-v2' if exposure else 'legacy-v1'
            row.setdefault('rerank_version','baseline')
        return rows
    return decorate
