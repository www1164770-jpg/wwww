"""Bounded loopback-only Ollama structured-output client."""

from __future__ import annotations

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .service import ModelFailure


_MAX_RESPONSE_BYTES = 65_536
_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "summary_zh": {"type": "string", "maxLength": 160},
        "tags_zh": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "evidence": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
    },
    "required": ["category", "confidence", "summary_zh", "tags_zh", "evidence"],
}


class OllamaClient:
    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        timeout_seconds: float,
        opener=urlopen,
    ) -> None:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "http"
            or (parsed.hostname or "").lower() not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None
            or parsed.password is not None
            or not parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Ollama endpoint must be a local HTTP URL")
        if not model.strip() or len(model.strip()) > 255:
            raise ValueError("Ollama model must be a bounded non-blank name")
        if not 0 < timeout_seconds <= 120:
            raise ValueError("Ollama timeout is outside the allowed range")
        self.endpoint = endpoint
        self.model = model.strip()
        self.timeout_seconds = float(timeout_seconds)
        self._opener = opener

    def analyze(self, payload: dict) -> dict:
        prompt = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        request_body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": _OUTPUT_SCHEMA,
                "prompt": (
                    "Return only JSON matching the schema. Use only facts present in this input: "
                    + prompt
                ),
                "options": {"temperature": 0, "num_ctx": 4096},
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            self.endpoint,
            data=request_body,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            body = error.read(4096).decode("utf-8", errors="ignore").casefold()
            if "out of memory" in body or "cuda" in body or "memory" in str(error.reason).casefold():
                raise ModelFailure("resource_exhausted") from error
            raise ModelFailure("unavailable") from error
        except (TimeoutError, socket.timeout) as error:
            raise ModelFailure("timeout") from error
        except URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                raise ModelFailure("timeout") from error
            raise ModelFailure("unavailable") from error
        except OSError as error:
            raise ModelFailure("unavailable") from error
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise ModelFailure("invalid_json")
        try:
            envelope = json.loads(raw.decode("utf-8"))
            content = envelope["response"]
            if not isinstance(content, str):
                raise TypeError
            result = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise ModelFailure("invalid_json") from error
        if not isinstance(result, dict):
            raise ModelFailure("invalid_json")
        return result
