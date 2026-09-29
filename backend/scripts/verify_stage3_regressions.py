"""Focused stage 3 regressions; preserves historical stage 1/2 reports."""
import json
import sys
from pathlib import Path
import verify_stage1_regressions as runner

ROOT=Path(__file__).resolve().parents[2]
PATTERNS=['test_ai_site_recommend_v1.py','test_site_search_v1.py','test_auth.py',
          'test_favorites_v1.py','test_career*.py','test_ai_retrieval_stage3.py','test_ai_model_transport_stage3.py']

def main():
    results=[]
    for pattern in PATTERNS:
        command=[sys.executable,'-m','unittest','discover','-s','tests','-p',pattern]
        run=runner.subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',
            env={**runner.os.environ,'PYTHONIOENCODING':'utf-8'})
        output=run.stdout+run.stderr
        counts=runner.re.findall(r'Ran (\d+) tests?',output)
        entry={'pattern':pattern,'exit_code':run.returncode,'tests_run':int(counts[-1]) if counts else None,
               'failures':runner.re.findall(r'^FAIL: .+$',output,runner.re.M),'errors':runner.re.findall(r'^ERROR: .+$',output,runner.re.M)}
        results.append(entry);print(json.dumps(entry),flush=True)
        if run.returncode: print(output[-12000:])
    (ROOT/'docs/recommendation/stage3-regression-results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    return int(any(row['exit_code'] for row in results))

if __name__=='__main__':raise SystemExit(main())
