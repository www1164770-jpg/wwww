"""Native daily entry; no schema initialization, seed import or scheduler startup."""
import os,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from dotenv import load_dotenv
load_dotenv(ROOT/'backend/.env',override=True)
from db_pool import validate_database_config
cfg=validate_database_config()
if (cfg['host'],cfg['port'],cfg['database'])!=('127.0.0.1',3306,'nav_site'):
    raise RuntimeError('Daily entry only accepts verified local nav_site')
if os.getenv('AI_REQUIREMENTS_MODEL_ENABLED')!='0' or os.getenv('RECOMMENDATION_RERANK_ENABLED')!='0':
    raise RuntimeError('Unaccepted model/rerank flags must remain off')
mode=sys.argv[1]
if mode=='backend':
    sys.argv=['flask','--app',str(ROOT/'backend/app.py'),'run','--host','127.0.0.1','--port','5000','--no-reload']
    runpy.run_module('flask',run_name='__main__')
elif mode=='worker':
    sys.argv=['search_sync.py','worker']
    runpy.run_path(str(ROOT/'backend/scripts/search_sync.py'),run_name='__main__')
else:raise ValueError('backend or worker required')
