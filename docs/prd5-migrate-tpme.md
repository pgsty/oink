# PRD 5 TPME Book migration recipe

This recipe migrates the authoritative Simplified Chinese TPME content to the
OINK `fig`, `tbl`, and language-correct `xref` primitives. It is deliberately
site-specific. Run it only after the site pins a published OINK release that
contains PRD 5.

## Observed source boundary

The tracked authority is `content/zh`; `content/en` may exist in a maintainer's
working copy but is not part of the clean repository checkout. Run the normal
site generation/translation workflow after the Simplified Chinese migration
rather than treating an untracked English directory as release input.

The 2026-08-14 inventory contains 31 numbered figures, 10 numbered tables, and
1,062 `/en/...#fragment` links in the Simplified Chinese source. The migration
classifies 44 as numbered figure/table references and 1,018 as generic stable
fragment references. All 1,062 become current-language `xref` calls. It also
converts the fake h6 captions without changing any public semantic ID.

## Dry-run and report

From the OINK checkout:

```sh
python3 scripts/migrations/prd5_book_migrate.py \
  --profile tpme \
  --root /path/to/tpme \
  --report /tmp/tpme-prd5.json > /tmp/tpme-prd5.diff
```

Dry-run is the default and never writes content. Review both the unified diff
and JSON report. Expected clean-checkout facts are:

```text
files_changed=12
figures=31
tables=10
references_numbered=44
references_generic=1018
skipped=0
idempotent=true
```

The converter accepts only an image followed by one recognized caption, or a
caption followed by one Markdown table. Simple emphasis/code/math in a legacy
caption is lowered to plain text because the Book caption contract is plain
text. Unknown markup is skipped instead of guessed.

## Apply and prove idempotency

Work on a dedicated branch, then explicitly write:

```sh
python3 scripts/migrations/prd5_book_migrate.py \
  --profile tpme \
  --root /path/to/tpme \
  --write \
  --report /tmp/tpme-prd5-written.json

python3 scripts/migrations/prd5_book_migrate.py \
  --profile tpme \
  --root /path/to/tpme \
  --no-diff \
  --report /tmp/tpme-prd5-second.json
```

The second report must contain `files_changed: 0`, empty `counts`, and
`idempotent: true`. Then run the site's language-generation workflow and
strict build. Validate rendered targets rather than only build status:

```sh
hugo --printPathWarnings --panicOnWarning --destination /tmp/tpme-public
python3 /path/to/oink/scripts/check-book.py --site-public /tmp/tpme-public
```

In the 2026-08-14 temporary-clone acceptance, the migrated site built 44 Hugo
pages on Hugo Extended 0.164.0 with warnings promoted to errors, and the
consumer output checker resolved every rendered xref to a real same-language
page/anchor with matching kind and number.

## Manual review boundary

Review the 31 image alternatives even though the migration preserves each
existing non-empty alt. Confirm the generated language tree uses the same
stable IDs and does not reintroduce `/en/` links. Do not delete the legacy
shortcode or update the production pin until the published theme tag resolves
without a local `replace`.
