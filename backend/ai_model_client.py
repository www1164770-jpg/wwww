"""Bounded shared DeepSeek JSON transport, extracted from ai_server.

One request, no automatic retry; no profile, retrieved page or credentials in logs.
"""
import json
import os
import time
import requests
from backend.crawler.analysis.service import ModelFailure


def complete_json(system, payload, *, timeout=8, max_tokens=1200):
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise ModelFailure("unavailable")
    if not 0 < timeout <= 30 or not 1 <= max_tokens <= 2000:
        raise ModelFailure("resource_exhausted")
    source = json.dumps(payload, ensure_ascii=False)
    if len(source) > 12000:
        raise ModelFailure("resource_exhausted")
    deadline = time.monotonic() + timeout
    try:
        with requests.post("https://api.deepseek.com/chat/completions",
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "system", "content": system},
                  {"role": "user", "content": source}], "response_format": {"type": "json_object"},
                  "temperature": 0, "max_tokens": max_tokens},
            timeout=(min(2,timeout), timeout), stream=True) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_content(2048):
                if time.monotonic() > deadline:
                    raise ModelFailure("timeout")
                body.extend(chunk)
                if len(body)>65536:
                    raise ModelFailure("resource_exhausted")
        envelope=json.loads(body)
        content=envelope["choices"][0]["message"]["content"]
        if not isinstance(content,str) or len(content)>12000:
            raise ModelFailure("invalid_json")
        result=json.loads(content)
        if not isinstance(result,dict):
            raise ModelFailure("invalid_schema")
        return result
    except requests.Timeout:
        raise ModelFailure("timeout") from None
    except requests.RequestException:
        raise ModelFailure("unavailable") from None
    except (ValueError,KeyError,TypeError,IndexError):
        raise ModelFailure("invalid_json") from None
