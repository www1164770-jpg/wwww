# Crawler runtime data

This directory contains local, replaceable crawler runtime data:

- `icons/`: content-addressed favicon/logo files used in later phases.
- `logs/`: structured JSON line logs.
- `tmp/`: bounded temporary downloads and atomic-write staging files.
- `pids/`: diagnostic PID markers; queue correctness never depends on them.

The contents of these directories are ignored by Git. Keep only the
documentation and `.gitkeep` markers in version control. Do not place
database URLs, credentials, cookies, access tokens, captured page bodies, or
personal data in this directory manually.
