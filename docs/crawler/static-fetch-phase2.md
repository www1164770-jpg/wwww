# Phase 2 static web crawler

Phase 2 extends the independent crawler infrastructure with a bounded static
HTTP pipeline. It does not execute JavaScript, log in to sites, bypass CAPTCHA,
classify content, publish records, or connect to the formal `nav_site` database.

## Data flow

1. A seed is normalized and enqueued as `static_fetch` in the existing
   `crawl_tasks` queue.
2. The worker leases it with the Phase 1 `FOR UPDATE SKIP LOCKED` lifecycle.
3. `NetworkPolicy` resolves every A and AAAA answer and rejects the complete
   target if any answer is not public. A request and every redirect force a new
   policy check before the transport opens or reuses a connection.
4. The crawler evaluates cached per-origin robots rules and waits for both the
   configured origin delay and a longer robots `Crawl-delay`, if present.
5. `StaticHttpFetcher` performs a bounded GET with explicit timeouts, manual
   redirects, limited retries, streaming reads, bounded gzip/deflate expansion,
   and a static document content-type allowlist.
6. HTML, Sitemap, RSS, or Atom metadata is parsed without storing the response
   body. Discovered URLs are normalized again and persisted.
7. Same-origin candidates within depth, page, sitemap, and run limits are
   enqueued idempotently. External URLs are recorded and never recursively
   scheduled by the default policy.
8. The result, links, child tasks, and task completion are committed through the
   crawler session factory. Temporary failures follow Phase 1 retry timing;
   permanent failures release their active dedupe identity as `dead`.

Long requests renew their task lease and heartbeat from an independent session.
A cancellation or crawl-run stop request interrupts rate-limit/retry/read waits
and moves an owned lease to `cancelled`.

## Security boundaries

- Only `http` and `https` are accepted. URL credentials, control characters,
  invalid ports, IPv6 zone identifiers, and oversized URLs are rejected.
- Hostnames are IDNA-normalized; fragments and common tracking parameters are
  removed. `www` and non-`www` names are never merged.
- Localhost, private, loopback, link-local, multicast, reserved, unspecified,
  documentation, benchmark, metadata, and private IPv4-mapped IPv6 targets are
  denied. Mixed public/private DNS answers deny the whole target.
- DNS cache lifetime is short, but fetches use forced revalidation and a
  policy-approved concrete address to prevent hostname rebinding between the
  check and connection.
- robots 404 means no rules. 401, 403, 429, 5xx, timeout, and network failure
  deny conservatively. The in-process cache stores check and expiry times;
  database-backed robots caching is intentionally deferred.
- HTML is parsed with `HTMLParser`, XML rejects DTD and entity declarations,
  and no parser is allowed to load network entities.
- Full bodies and sensitive URL query values are not written to logs or emitted
  by JSON CLI output.

## Persistence

Migration `0002_static_fetch` adds only the crawler-owned tables:

- `fetch_results`: one result identity per task, plus a unique normalized-final
  fingerprint/content-hash pair so unchanged content does not create history
  noise.
- `discovered_links`: one normalized URL per source result, including relation,
  discovery source, depth, origin classification, enqueue state, and bounded
  JSON metadata.

Both tables use InnoDB, `utf8mb4`, BIGINT keys/counters where required, native
JSON, named foreign keys, unique constraints, and lookup indexes. The migration
runner accepts exactly `zhihui_crawler` or `zhihui_crawler_test`; it has no
downgrade path, seed, database creation, or formal-database fallback.

## CLI

Phase 1 commands remain available. Phase 2 adds:

```text
enqueue-url <url> --json
fetch-once <url> --json
worker-once --json
worker-run --max-jobs 20 --json
task-show <task_uid> --json
result-show <result_uid> --json
```

`enqueue-url` performs no fetch. `fetch-once` still creates an official queue
task and runs it through the worker. Worker commands are bounded and do not
translate database failures into an empty queue response.

## Limits and tests

All Phase 2 environment values are declared in
`backend/crawler/.env.example`, parsed without database or network I/O, and
validated against positive upper and lower bounds.

Unit tests cover normalization, SSRF/DNS rebinding, robots, per-origin limiting,
HTTP errors and compression, HTML, Sitemap, feed parsing, persistence, worker
states, and CLI contracts. The loopback HTTP fixture is reachable only through
an injected resolver and transport; the production policy continues to reject
localhost. The real MySQL integration test strictly checks
`DATABASE() == zhihui_crawler_test`, uses two workers, and removes only rows
tagged by its unique run identifiers.
