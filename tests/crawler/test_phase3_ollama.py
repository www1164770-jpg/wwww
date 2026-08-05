from __future__ import annotations

from io import BytesIO
import json
import socket
import unittest
from urllib.error import HTTPError, URLError

from backend.crawler.analysis import ModelFailure
from backend.crawler.analysis.ollama import OllamaClient


class FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = BytesIO(payload)

    def read(self, amount=-1):
        return self._payload.read(amount)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class PhaseThreeOllamaTests(unittest.TestCase):
    def test_local_client_uses_bounded_schema_request_and_parses_json(self) -> None:
        calls = []
        inner = {
            "category": "education",
            "confidence": 0.9,
            "summary_zh": "教育网站。",
            "tags_zh": ["教育"],
            "evidence": ["courses"],
        }

        def opener(request, timeout):
            calls.append((request, timeout))
            return FakeResponse(json.dumps({"response": json.dumps(inner)}).encode())

        client = OllamaClient(
            endpoint="http://127.0.0.1:11434/api/generate",
            model="qwen-test",
            timeout_seconds=3,
            opener=opener,
        )
        result = client.analyze({"schema_version": "v1", "evidence_text": "courses"})

        self.assertEqual(result, inner)
        self.assertEqual(len(calls), 1)
        request, timeout = calls[0]
        self.assertEqual(timeout, 3)
        body = json.loads(request.data)
        self.assertEqual(body["model"], "qwen-test")
        self.assertFalse(body["stream"])
        self.assertIn("format", body)
        self.assertNotIn("Authorization", dict(request.header_items()))

    def test_remote_endpoint_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            OllamaClient(
                endpoint="https://models.example.com/api/generate",
                model="x",
                timeout_seconds=3,
            )

    def test_timeout_invalid_json_and_oom_are_classified(self) -> None:
        cases = (
            (lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError(socket.timeout())), "timeout"),
            (lambda *_args, **_kwargs: FakeResponse(b"not-json"), "invalid_json"),
            (
                lambda request, timeout: (_ for _ in ()).throw(
                    HTTPError(request.full_url, 500, "out of memory", {}, BytesIO(b"out of memory"))
                ),
                "resource_exhausted",
            ),
        )
        for opener, code in cases:
            with self.subTest(code=code):
                client = OllamaClient(
                    endpoint="http://localhost:11434/api/generate",
                    model="qwen-test",
                    timeout_seconds=1,
                    opener=opener,
                )
                with self.assertRaises(ModelFailure) as caught:
                    client.analyze({"evidence_text": "bounded"})
                self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main()
