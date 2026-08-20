## Summary

Describe the user-visible change and any downstream compatibility impact.

## Verification

- [ ] `python3 bin/check-i18n.py`
- [ ] `hugo --source tests/site --printPathWarnings --panicOnWarning`
- [ ] The OINK regression site's browser tests pass, when the change affects rendered output.
- [ ] `CHANGELOG.md` covers user-visible or breaking changes.
- [ ] Upstream copyright headers remain intact in inherited files.
