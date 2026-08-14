# PRD 5 pg-internal Book migration recipe

This recipe targets the tracked Chinese `content/` tree. The separate imported
English work in the maintainer checkout is not silently included: it has a
different split-page structure and must be migrated after that import becomes
an intentional repository surface.

## Deterministic forms

The profile recognizes bold or italic Chinese/English Figure captions directly
before or after one image, and numbered table captions directly before one
Markdown table. It inventories every target before rewriting prose, so a
reference that appears before its table or figure still resolves correctly.
Only a globally unique kind/number target is rewritten; ambiguous references
remain unchanged.

```sh
python3 scripts/migrations/prd5_book_migrate.py \
  --profile pg-internal \
  --root /path/to/pg-internal \
  --report /tmp/pg-internal-prd5.json > /tmp/pg-internal-prd5.diff
```

The 2026-08-14 tracked Chinese inventory produces:

```text
files_changed=11
figures=119
tables=5
references_numbered=136
skipped=3
idempotent=true
```

The three skipped images are concrete manual-review items, not hidden losses:

- `content/ch3.md`: an indented plan image without a unique adjacent numbered
  caption;
- `content/ch7.md`: `/img/fig-7-03.png` with no unique numbered caption;
- `content/ch9.md`: `/img/fig-9-18.png`, whose preceding text omits the Figure
  label.

## Apply and validate

The repository may contain unrelated import sources and scripts. Apply only on
a dedicated branch and do not include those unrelated paths in the migration
commit.

```sh
python3 scripts/migrations/prd5_book_migrate.py \
  --profile pg-internal \
  --root /path/to/pg-internal \
  --write \
  --report /tmp/pg-internal-prd5-written.json

python3 scripts/migrations/prd5_book_migrate.py \
  --profile pg-internal \
  --root /path/to/pg-internal \
  --no-diff \
  --report /tmp/pg-internal-prd5-second.json
```

Require a zero-change second report. Build with the published OINK pin and the
consumer Goldmark passthrough configuration, then validate the output:

```sh
hugo --printPathWarnings --panicOnWarning --destination /tmp/pg-internal-public
python3 /path/to/oink/scripts/check-book.py \
  --site-public /tmp/pg-internal-public
```

The 2026-08-14 temporary-clone acceptance built 36 Hugo pages on Extended
0.164.0 with warnings fatal. The output checker resolved every migrated xref,
verified each kind/number pair, and found no duplicate page IDs or empty alt on
a numbered figure.

## Manual review boundary

Repair the three skipped images deliberately, then rerun the profile and
expect them either to migrate or remain listed with a documented reason. The
new English split-page tree needs its own inventory and page-reference mapping;
do not point the Chinese profile at it. Delete the local passthrough hook only
after the theme pin contains the PRD 5 hook and both delimiter math and the
`eq` escape hatch render in the deployed site.
