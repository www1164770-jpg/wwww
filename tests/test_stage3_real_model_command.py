import contextlib
import io
import json
import os
from pathlib import Path
import sys
from uuid import uuid4
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from backend.scripts.verify_stage3_real_model import main


class RealModelCommandTests(unittest.TestCase):
    def test_not_executed_gates_never_use_network_or_database(self):
        for env,flags,reason in [({},['--run'],'missing_credentials'),
            ({'DEEPSEEK_API_KEY':'do-not-print'},[],'run_flag_required'),
            ({'DEEPSEEK_API_KEY':'do-not-print','AI_REQUIREMENTS_MODEL_ENABLED':'0'},['--run'],'model_disabled')]:
            with self.subTest(reason=reason):
                output=ROOT/'artifacts'/f'stage3-gate-{uuid4().hex}.json';console=io.StringIO()
                with patch.dict(os.environ,env,clear=True),patch('backend.scripts.verify_stage3_real_model.load_dotenv'),patch('backend.scripts.verify_stage3_real_model.configured_model') as model,patch('sqlalchemy.create_engine') as engine,contextlib.redirect_stdout(console):
                    self.assertEqual(main(['--database','ai_retrieval_012345abcdef_test','--output',str(output),*flags]),0)
                model.assert_not_called();engine.assert_not_called()
                report=json.loads(output.read_text(encoding='utf-8'))
                self.assertEqual(report['status'],'not_executed');self.assertFalse(report['real_model_executed'])
                self.assertEqual(report['reason'],reason);self.assertEqual(report['cases'],[])
                self.assertNotIn('do-not-print',output.read_text(encoding='utf-8')+console.getvalue())
                output.unlink()

    def test_refuses_business_database(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as result:
            main(['--run','--database','nav_site'])
        self.assertEqual(result.exception.code,2)


if __name__=='__main__':unittest.main()
