import json
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT)]
from ai_model_client import complete_json
from backend.crawler.analysis.service import ModelFailure


class ModelTransportTests(unittest.TestCase):
    def test_unverified_claim_does_not_prove_free(self):
        from ai_retrieval import facts
        values,_=facts({'pricing_model':'free','resource_metadata':{'pricing_model':{'source_kind':'extracted','verified_at':None}}})
        self.assertIsNone(values['pricing'])

    def test_missing_key_does_not_call_provider(self):
        with patch.dict('os.environ',{},clear=True),patch('ai_model_client.requests.post') as post:
            with self.assertRaises(ModelFailure): complete_json('rules',{})
            post.assert_not_called()

    def test_timeout_is_sanitized(self):
        with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'test-only-secret'}),patch('ai_model_client.requests.post',side_effect=requests.Timeout('private internal detail')):
            with self.assertRaises(ModelFailure) as result: complete_json('rules',{})
            self.assertNotIn('private',str(result.exception))
            self.assertNotIn('secret',str(result.exception))

    def test_response_limits_and_json(self):
        fixtures=[(b'not json',False),(b'x'*65537,False),
            (json.dumps({'choices':[{'message':{'content':'[]'}}]}).encode(),False),
            (json.dumps({'choices':[{'message':{'content':'{"conditions":[]}'}}]}).encode(),True)]
        for body,valid in fixtures:
            with self.subTest(valid=valid,size=len(body)):
                response=MagicMock();response.__enter__.return_value=response
                response.iter_content.return_value=[body]
                with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture'}),patch('ai_model_client.requests.post',return_value=response) as post:
                    if valid: self.assertEqual(complete_json('rules',{}),{'conditions':[]})
                    else:
                        with self.assertRaises(ModelFailure): complete_json('rules',{})
                    self.assertEqual(post.call_count,1)

    def test_input_and_token_limits_before_network(self):
        with patch.dict('os.environ',{'DEEPSEEK_API_KEY':'fixture'}),patch('ai_model_client.requests.post') as post:
            for payload,options in [({'q':'x'*12001},{}),({}, {'max_tokens':2001}),({}, {'timeout':31})]:
                with self.assertRaises(ModelFailure): complete_json('rules',payload,**options)
            post.assert_not_called()


if __name__=='__main__':unittest.main()
