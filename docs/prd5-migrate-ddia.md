# PRD 5 DDIA Book migration recipe

This recipe has two independent profiles because DDIA v2 and v1 use different
legacy conventions. It preserves the existing public anchors and refuses to
invent numbers for decorative images.

## DDIA v2: old `figure` shortcode

The current Simplified Chinese v2 source contains exactly 131 calls to the
site-local `figure` shortcode. They are not all figures:

- 106 are numbered figures and become self-closing `fig` calls;
- 3 are numbered Markdown tables and become paired `tbl` calls;
- 22 are numbered code examples and become semantic h4 headings with their
  existing IDs, not fake Figures.

The 304 links to those `#fig_*`/`#tab_*` targets are also classified rather
than blindly replaced: numbered figure/table references become kind-aware
`xref`, example/explicit-anchor references (including links inside example
headings) become anchor-only `xref`, and the one link embedded in a numbered
Figure caption is flattened to visible plain text to honor the frozen
plain-caption contract. The report counters sum to the full 304-link inventory.

```sh
python3 scripts/migrations/prd5_book_migrate.py \
  --profile ddia-v2 \
  --root /path/to/ddia \
  --report /tmp/ddia-v2-prd5.json > /tmp/ddia-v2-prd5.diff
```

Expected 2026-08-14 clean-checkout facts:

```text
files_changed=14
figures=106
tables=3
examples=22
references_numbered=245
references_generic=58
caption_links_flattened=1
skipped=0
idempotent=true
```

`245 + 58 + 1 = 304`; the three table links are included in
`references_numbered`, so the original 301 `#fig_*` links and three `#tab_*`
links are all accounted for.

## DDIA v1: bare images and bold captions

The v1 profile pairs only a bare image with one adjacent bold numbered
caption. Its stable ID derives from the existing image basename, and a link
to that exact image becomes a numbered xref only when the link label agrees
with the caption number.

```sh
python3 scripts/migrations/prd5_book_migrate.py \
  --profile ddia-v1 \
  --root /path/to/ddia \
  --report /tmp/ddia-v1-prd5.json > /tmp/ddia-v1-prd5.diff
```

Expected facts are 90 migrated figures, 203 matching image references, and 14
deliberate skips: the twelve chapter maps, one title image, and one external
poster. Those 14 images have no numbered caption and must not be turned into
Book figures merely to reach a larger conversion count.

## Apply, second-run check, and site validation

Apply the profiles separately so their reports remain attributable:

```sh
python3 scripts/migrations/prd5_book_migrate.py --profile ddia-v2 \
  --root /path/to/ddia --write --report /tmp/ddia-v2-written.json
python3 scripts/migrations/prd5_book_migrate.py --profile ddia-v1 \
  --root /path/to/ddia --write --report /tmp/ddia-v1-written.json

python3 scripts/migrations/prd5_book_migrate.py --profile ddia-v2 \
  --root /path/to/ddia --no-diff --report /tmp/ddia-v2-second.json
python3 scripts/migrations/prd5_book_migrate.py --profile ddia-v1 \
  --root /path/to/ddia --no-diff --report /tmp/ddia-v1-second.json
```

Both second reports must say `files_changed: 0`. Regenerate the Traditional
Chinese variants from their authorities, then build every configured language
with warnings promoted to errors and run:

```sh
python3 /path/to/oink/scripts/check-book.py --site-public /tmp/ddia-public
```

The 2026-08-14 temporary-clone acceptance built ZH 57, TW 55, v1 49, and v1-TW
49 pages on Hugo Extended 0.164.0; the rendered consumer checker found no
missing target, kind/number mismatch, duplicate page ID, or empty numbered
figure alternative.

## Manual review boundary

Review the 14 intentionally unnumbered v1 images and all captions whose math
was lowered to readable plain text. Confirm v2 generated-language content is
regenerated rather than directly hand-edited. Remove the local `figure.html`
only after the published theme pin, strict site build, and hosted fragment
smoke tests all pass.
