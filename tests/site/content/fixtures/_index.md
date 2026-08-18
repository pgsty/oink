---
title: Fixtures
linkTitle: Fixtures
description: Narrow pages that pin theme behaviour for the check scripts and the output goldens.
icon: fa-solid fa-flask
# This section is its own sidebar root: /docs/ is the flat component
# reference, and the fixture tree (including the nested guides) is separate.
sidebar_root_for: self
cascade:
  type: docs
---

These pages are not documentation. Each one exercises one slice of the theme so
`bin/check-*.py` and the goldens have something stable to compare against. They
sit outside `/docs/`, which carries the component reference, and they are not in
the site navigation.
