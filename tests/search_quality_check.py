#!/usr/bin/env python3
"""Small regression check for research search behavior.

Runs against a temporary research corpus so it does not mutate the user's real
library. Intended as a fast guard for FTS query safety, snippets, and linked
external project indexing.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research.py"


def run(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(RESEARCH), *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def write_entry(path: Path) -> None:
    path.write_text(
        """---
slug: research-plugin.search-quality
title: Research Plugin Search Quality
topics: [research-plugin]
projects: [research-plugin]
status: evergreen
workflow: synthesis
created: 2026-05-27
reviewed: 2026-05-27
topic_velocity: high
tags: [search-quality]
confidence: partial
corroboration: 1
sources: []
related: []
inbound: []
---
## TL;DR

The research-plugin search path needs safe plain-text parsing, snippets, and parser confidence ranking.

## Notes

Search should handle hyphenated terms like research-plugin without requiring raw FTS5 syntax.
Parser confidence should influence future evidence ranking.

## Raw

Local fixture for search quality checks.
"""
    )


def write_linked_project(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "heath-made-to-stick.md").write_text(
        """# Heath and Heath - SUCCESs Framework

Made to Stick explains why some ideas are memorable. This linked research file
is intentionally outside the canonical research topics tree.
"""
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="research-search-quality-") as td:
        root = Path(td)
        env = os.environ.copy()
        env["RESEARCH_CONTENT_DIR"] = str(root / "content")
        env["RESEARCH_INDEX_DIR"] = str(root / "index")
        env["RESEARCH_PROJECTS_DIR"] = str(root / "projects")

        failures: list[str] = []
        init = run(["init"], env)
        require(init.returncode == 0, f"init failed: {init.stderr}", failures)

        entry = root / "entry.md"
        write_entry(entry)
        save = run(["save", "--file", str(entry)], env)
        require(save.returncode == 0, f"save failed: {save.stderr}", failures)

        linked_dir = root / "external" / "speaksavvy" / "docs" / "research"
        write_linked_project(linked_dir)
        link = run(["link-project", "speaksavvy", str(linked_dir)], env)
        require(link.returncode == 0, f"link-project failed: {link.stderr}", failures)

        hyphen = run(["search", "research-plugin", "--project", "research-plugin", "--json"], env)
        require(hyphen.returncode == 0, f"hyphen search failed: {hyphen.stderr}", failures)
        hyphen_rows = json.loads(hyphen.stdout or "[]")
        require(
            any(r.get("slug") == "research-plugin.search-quality" for r in hyphen_rows),
            "hyphen search did not find canonical research-plugin entry",
            failures,
        )
        require(
            any("[" in (r.get("snippet") or "") for r in hyphen_rows),
            "hyphen search did not return highlighted snippets",
            failures,
        )

        linked = run(["search", "Made Stick", "--project", "speaksavvy", "--json"], env)
        require(linked.returncode == 0, f"linked search failed: {linked.stderr}", failures)
        linked_rows = json.loads(linked.stdout or "[]")
        require(
            any(r.get("kind") == "linked" and r.get("relpath") == "heath-made-to-stick.md" for r in linked_rows),
            "linked search did not find external linked project file",
            failures,
        )

        entries_only = run(["search", "Made Stick", "--project", "speaksavvy", "--entries-only", "--json"], env)
        require(entries_only.returncode == 0, f"entries-only search failed: {entries_only.stderr}", failures)
        require(json.loads(entries_only.stdout or "[]") == [], "entries-only returned linked files", failures)

        if failures:
            print("FAIL search quality checks:")
            for failure in failures:
                print(f"- {failure}")
            return 1

    print("PASS search quality checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
