#!/usr/bin/env python3
"""OINK 0.6 (v5 component API) content migration toolkit.

    scripts/migrations/oink06.py report  --sites ~/pgsty/site-a ~/www/ddia [--json r.json] [--md r.md]
    scripts/migrations/oink06.py migrate --site ~/pgsty/site-a [--only callout,tabs] [--write] [--json out.json]
    scripts/migrations/oink06.py check   --site ~/pgsty/site-a

Dry-run is the default; ``--write`` rewrites files atomically. A second run
must report zero changes. Constructs the scripts cannot express are left
untouched and listed with file:line and the reason. Stdlib only.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from oink06.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
