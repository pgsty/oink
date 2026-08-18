#!/usr/bin/env python3
"""Validate the dry-run-first Book migration profiles."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MIGRATOR = ROOT / "bin/migrations/book_figures.py"


class MigrationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MigrationError(message)


def write(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def invoke(root: Path, profile: str, report: Path, *, write_changes: bool) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    command = [
        sys.executable,
        str(MIGRATOR),
        "--profile",
        profile,
        "--root",
        str(root),
        "--no-diff",
        "--report",
        str(report),
    ]
    if write_changes:
        command.append("--write")
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    require(result.returncode == 0, f"{profile} migration failed:\n{result.stdout}{result.stderr}")
    require(report.exists(), f"{profile} emitted no JSON report")
    return result, json.loads(report.read_text(encoding="utf-8"))


def check_profile(
    root: Path,
    profile: str,
    expected_counts: dict[str, int],
    expected_skips: int,
    markers: tuple[str, ...],
) -> None:
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*.md")}
    _, dry = invoke(root, profile, root / "dry.json", write_changes=False)
    after_dry = {path.relative_to(root): path.read_bytes() for path in root.rglob("*.md")}
    require(before == after_dry, f"{profile} dry-run changed source files")
    require(dry.get("schema") == 1, f"{profile} report schema changed")
    require(dry.get("profile") == profile, f"{profile} report lost profile identity")
    require(dry.get("counts") == expected_counts, f"{profile} counts changed: {dry.get('counts')}")
    require(len(dry.get("skipped", [])) == expected_skips, f"{profile} skip count changed: {dry.get('skipped')}")
    require(dry.get("idempotent") is True, f"{profile} dry-run is not internally idempotent")
    require(dry.get("files_changed", 0) > 0, f"{profile} fixture produced no migration")
    require(len(str(dry.get("diff_sha256", ""))) == 64, f"{profile} report lost diff digest")

    _, written = invoke(root, profile, root / "written.json", write_changes=True)
    require(written.get("counts") == expected_counts, f"{profile} write counts differ from dry-run")
    migrated = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.md"))
    for marker in markers:
        require(marker in migrated, f"{profile} output lacks {marker}")
    require("/ >}}" not in migrated, f"{profile} emitted invalid self-closing shortcode syntax")

    _, second = invoke(root, profile, root / "second.json", write_changes=False)
    require(second.get("files_changed") == 0, f"{profile} second run is not a no-op")
    require(second.get("counts") == {}, f"{profile} second run still reports rewrites")
    require(second.get("idempotent") is True, f"{profile} second report is not idempotent")
    require(len(second.get("skipped", [])) == expected_skips, f"{profile} ambiguity inventory changed after migration")


def fixture_tpme(root: Path) -> None:
    write(
        root / "content/zh/ch1.md",
        """---
title: Chapter
---

[图 1-1](/en/ch1#one)与[章节](/en/ch2#stable)。

![明确替代文本](/fig/one.png)

###### 图 1-1. 含 *强调* 的图注 {#one}

[表 1-1](/en/ch1#rows)：

###### 表 1-1. 行 {#rows}

| A | B |
| - | - |
| 1 | 2 |
""",
    )


def fixture_ddia_v2(root: Path) -> None:
    write(
        root / "content/zh/ch1.md",
        """---
title: Chapter
---

[图 1-1](/ch1#fig_one)和[表 1-1](/ch1#tab_one)。

{{< figure src="/fig/one.png" id="fig_one" caption="图 1-1. 采用[表 1-1](/ch1#tab_one)的图注。" class="w-full my-4" >}}

{{< figure id="tab_one" title="表 1-1. 行" class="w-full my-4" >}}

| A | B |
| - | - |
| 1 | 2 |

{{< figure id="example_one" title="示例 1-1. 查询[图 1-1](/ch1#fig_one)" class="w-full my-4" >}}

```sql
select 1;
```
""",
    )


def fixture_ddia_v1(root: Path) -> None:
    write(
        root / "content/v1/ch1.md",
        """---
title: Chapter
---

[图 1-1](/v1/one.png)。

![](/v1/one.png)

**图 1-1  如果 $w + r > n$，读取保持重叠。**

正文继续，下面是没有编号的章节地图。

![](/map/ch01.png)
""",
    )


def fixture_pg_internal(root: Path) -> None:
    write(
        root / "content/ch1.md",
        """---
title: Chapter
---

表1.1先被引用，图1.1也是如此。

**图1.1 结构**

![结构](/img/fig-1-01.png)

**表 1.1 行**

| A | B |
| - | - |
| 1 | 2 |

![没有图注](/img/orphan.png)
""",
    )


def main() -> int:
    try:
        require(MIGRATOR.exists(), "Book figure migration tool is missing")
        with tempfile.TemporaryDirectory(prefix="oink-components-migrations-") as temp:
            base = Path(temp)
            cases = (
                (
                    "tpme",
                    fixture_tpme,
                    {"figures": 1, "references_generic": 1, "references_numbered": 2, "tables": 1},
                    0,
                    ('{{< fig num="1-1" id="one"', '{{< tbl num="1-1" id="rows"', '{{< xref page="/ch2" anchor="stable" >}}'),
                ),
                (
                    "ddia-v2",
                    fixture_ddia_v2,
                    {"caption_links_flattened": 1, "examples": 1, "figures": 1, "references_numbered": 3, "tables": 1},
                    0,
                    ('{{< fig num="1-1" id="fig_one"', '{{< tbl num="1-1" id="tab_one"', '#### 示例 1-1. 查询{{< xref fig="1-1"'),
                ),
                (
                    "ddia-v1",
                    fixture_ddia_v1,
                    {"figures": 1, "references_numbered": 1},
                    1,
                    ('{{< fig num="1-1" id="fig_one"', '{{< xref fig="1-1" page="/ch1" anchor="fig_one" >}}'),
                ),
                (
                    "pg-internal",
                    fixture_pg_internal,
                    {"figures": 1, "references_numbered": 2, "tables": 1},
                    1,
                    ('{{< fig num="1.1"', '{{< tbl num="1.1"', '{{< xref tbl="1.1" anchor="tbl-1.1" >}}'),
                ),
            )
            for profile, create, counts, skips, markers in cases:
                root = base / profile
                create(root)
                check_profile(root, profile, counts, skips, markers)
    except (OSError, MigrationError, json.JSONDecodeError) as exc:
        print(f"migration checks failed: {exc}", file=sys.stderr)
        return 1
    print("Book migration checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
