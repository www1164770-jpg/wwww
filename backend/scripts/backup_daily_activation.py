"""Local daily activation backup; never changes the source database."""
import hashlib,json,os,re,shutil,subprocess,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from db_pool import validate_database_config
import pymysql
cfg=validate_database_config()
assert (cfg['host'],cfg['port'],cfg['database'])==('127.0.0.1',3306,'nav_site')
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
folder=Path(os.environ['LOCALAPPDATA'])/'zhihangyu-backups'/stamp
folder.mkdir(parents=True,exist_ok=False)
for name in ['backend/.env','.env','compose.yaml','start.bat','stop.bat','status.bat','.gitignore','docs/release/local-integration-readiness.md']:
    source=ROOT/name
    if source.exists():
        dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
def snapshot(database):
    with pymysql.connect(**{**cfg,'database':database}) as conn,conn.cursor() as c:
        c.execute('SHOW FULL TABLES');tables=[r[0] for r in c.fetchall() if r[1]=='BASE TABLE'];result={}
        for table in tables:
            assert re.fullmatch(r'\w+',table)
            c.execute(f'SELECT COUNT(*) FROM `{table}`');count=c.fetchone()[0]
            c.execute(f'CHECKSUM TABLE `{table}`');checksum=c.fetchone()[1]
            result[table]={'count':count,'checksum':checksum}
        return result
before=snapshot('nav_site')
env={**os.environ,'MYSQL_PWD':cfg['password']}
common=['--host=127.0.0.1','--port=3306','--user='+cfg['user'],'--default-character-set=utf8mb4']
dump=folder/'nav_site.sql'
subprocess.run(['mysqldump',*common,'--single-transaction','--routines','--triggers','--events','--hex-blob','--no-tablespaces','--set-gtid-purged=OFF','--skip-add-drop-table','--result-file='+str(dump),'nav_site'],env=env,check=True,capture_output=True)
assert dump.stat().st_size>1000
restore='nav_site_restore_'+stamp.replace('-','')
with pymysql.connect(**cfg) as conn,conn.cursor() as c:c.execute(f'CREATE DATABASE `{restore}` CHARACTER SET utf8mb4')
with dump.open('rb') as stream:
    subprocess.run(['mysql',*common,'--database='+restore],stdin=stream,env=env,check=True,capture_output=True)
restored=snapshot(restore);after=snapshot('nav_site')
assert before==restored==after,'Backup restore/content check failed: stop all activation'
report={'backup_directory':str(folder),'dump':str(dump),'dump_bytes':dump.stat().st_size,'sha256':hashlib.sha256(dump.read_bytes()).hexdigest(),'restore_database':restore,'all_tables_equal':True,'tables':before,'source':{'host':cfg['host'],'port':cfg['port'],'database':cfg['database']}}
(folder/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
out=ROOT/'artifacts/daily-activation';out.mkdir(exist_ok=True)
(out/'backup-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='tables'}))
