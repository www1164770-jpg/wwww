# Phase 3 analysis, risk, and icon assets

Phase 3 consumes immutable successful `fetch_results` rows. It never refetches
page content and never imports or connects to the formal application database.
All tables and tasks remain inside the independently configured crawler MySQL
database.

## Data flow

1. When `CRAWLER_ANALYSIS_ENABLED=true`, completion of a static fetch
   idempotently enqueues an `analysis` task containing only stable UIDs,
   versions, and the content hash.
2. The analysis worker loads the bounded metadata and `text_excerpt` already
   stored by Phase 2. Deterministic rules detect language, category, quality,
   summary, tags, and minimal evidence hashes.
3. High-confidence results do not call a model. Low-confidence results call
   only the configured loopback Ollama endpoint with a truncated evidence
   payload and a strict JSON output schema.
4. Timeout, invalid JSON, invalid evidence, unavailable service, or resource
   exhaustion preserves the rule result as `model_unavailable`; it does not
   lose the task or claim model success.
5. Hard risk rules run against the source evidence after analysis. Adult,
   gambling, illegal drugs, weapons, phishing, malware, piracy, and violent
   extremist signals are rejected regardless of model output. Ambiguous or
   low-quality results become `review_required`; only high-confidence results
   without a hard rule become `approved`.
6. When `CRAWLER_ICON_FETCH_ENABLED=true`, a non-rejected decision can enqueue
   one `icon_fetch` task. Every request and redirect rechecks DNS/SSRF policy,
   robots, and origin rate limits before downloading bounded image bytes.

## Persistence

Forward migration `0003_analysis_risk_assets` adds only crawler-owned tables:

- `analysis_results`: immutable `(fetch_result_id, analysis_version)` output;
- `risk_decisions`: immutable `(analysis_result_id, decision_version)` output;
- `icon_assets`: content hash, verified MIME/dimensions, safe source URL, and
  relative cache path.

Every table has a stable UID and foreign keys back to crawler-owned data. No
downgrade, delete, truncate, database creation, or formal database reference is
present. The migration runner still accepts only `zhihui_crawler` or
`zhihui_crawler_test`.

## Model boundary

`CRAWLER_OLLAMA_ENDPOINT` must be an unauthenticated loopback HTTP URL using
`127.0.0.1`, `localhost`, or `::1`. The client sends no cookies,
authorization header, database value, full body, or URL query evidence. The
response is byte-bounded and both the Ollama envelope and inner result must be
valid JSON. Model evidence must be present in the supplied source excerpt.

## Icon boundary

The icon cache root is `CRAWLER_ICON_ROOT`. Files are named by SHA-256 and
sharded as `<byte-1>/<byte-2>/<sha256>.<extension>`. Writes use a temporary
file and atomic replacement. The validator accepts bounded PNG, JPEG, GIF,
WebP, and ICO headers whose declared MIME matches; SVG and unknown types are
rejected. Byte, width, height, and total pixel limits block oversized images
and decompression-bomb dimensions without requiring an image decoder package.

## Configuration

Phase 3 is rollout-safe and disabled by default:

```text
CRAWLER_ANALYSIS_ENABLED=false
CRAWLER_ICON_FETCH_ENABLED=false
CRAWLER_ANALYSIS_CONFIDENCE_THRESHOLD=0.85
CRAWLER_ANALYSIS_RULE_VERSION=analysis-rules-v1
CRAWLER_RISK_RULE_VERSION=risk-rules-v1
CRAWLER_OLLAMA_ENDPOINT=http://127.0.0.1:11434/api/generate
CRAWLER_OLLAMA_MODEL=qwen2.5:3b
CRAWLER_OLLAMA_TIMEOUT_SECONDS=20
CRAWLER_ICON_MAX_BYTES=1048576
CRAWLER_ICON_MAX_PIXELS=16777216
CRAWLER_ICON_MAX_REDIRECTS=3
```

## CLI and verification

The commands are bounded and process no more than one or `--max-jobs` tasks:

```text
analysis-once --json
analysis-run --max-jobs 20 --json
icon-once --json
icon-run --max-jobs 20 --json
```

Run the complete standard-library regression with the explicit test crawler
database configured:

```text
python -m unittest discover -s tests/crawler -t . -p "test_*.py" -v
```

The MySQL integration tests validate `DATABASE() == zhihui_crawler_test`
before use. They never fall back to the formal database.
