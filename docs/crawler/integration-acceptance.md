# Crawler isolated integration acceptance

This runbook never uses the application default database or production
`nav_site`.  Configure only isolated targets, then run the commands below from
the repository root.

1. Check configuration without opening a connection:

   ```powershell
   python -m backend.crawler.cli integration-readiness --json
   ```

2. Confirm the crawler URL points to `zhihui_crawler` or
   `zhihui_crawler_test`, then run the guarded migration twice:

   ```powershell
   python -m backend.crawler.cli db-check --json
   python -m backend.crawler.cli migrate --json
   python -m backend.crawler.cli migrate --json
   ```

3. In a separate test process only, set `CRAWLER_DATABASE_URL` to the value of
   `CRAWLER_TEST_DATABASE_URL` and run:

   ```powershell
   python -m unittest discover -s tests/crawler -p "test_*.py" -v
   ```

4. Enable a publish target only when all of these hold: sync is explicitly
   enabled, a separate target URL and allowed database name are configured,
   `SELECT DATABASE()` matches that exact name, and it is neither crawler
   database.  The current code intentionally has no real target schema mapping;
   keep publication disabled until that isolated adapter is implemented and
   tested.

Acceptance requires `failures=0`, `errors=0`, `skipped=0`, plus an isolated
publish E2E proving duplicate/retry recovery leaves exactly one target record.
