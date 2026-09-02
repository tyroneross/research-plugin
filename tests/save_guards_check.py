#!/usr/bin/env python3
"""Contract suite for the two non-blocking save-time guards.

Both guards are advisory: they name a problem the author can still choose to
accept. Neither may block a save or change an exit code, so these tests assert
the warning CONTENT and, separately, that a save carrying both problems still
returns 0.
"""

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _load_research():
    spec = importlib.util.spec_from_file_location("_research_mod", REPO / "research.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load_research()

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {label}")
    else:
        FAILURES.append(f"{label}{': ' + detail if detail else ''}")
        print(f"  FAIL {label} {detail}")


# --- Guard 1: provenance -----------------------------------------------------

def test_provenance() -> None:
    print("provenance guard")

    complete = [{"url": "https://a.example/x", "content_hash": "sha256:" + "0" * 64, "locator": "section 2"}]
    check("silent when every source has hash + locator", R.save_provenance_warnings(complete) == [])

    unknown_ok = [{
        "url": "https://a.example/x",
        "content_hash": "sha256:" + "0" * 64,
        "locator_unknown_reason": "single-page document",
    }]
    check("accepts an explicit locator_unknown_reason", R.save_provenance_warnings(unknown_ok) == [])

    bare = [{"url": "https://a.example/x"}, {"url": "https://b.example/y"}]
    out = R.save_provenance_warnings(bare)
    check("warns on bare url sources", bool(out))
    check("names the count", any("2 of 2" in line for line in out), str(out[:1]))
    check("names the merge-gate consequence", any("merge gate" in line for line in out))
    check("names each offending url", any("a.example" in l for l in out) and any("b.example" in l for l in out))

    plain_strings = ["https://c.example/z"]
    check("handles plain-string sources", bool(R.save_provenance_warnings(plain_strings)))

    check("empty source list is silent", R.save_provenance_warnings([]) == [])

    many = [{"url": f"https://e.example/{i}"} for i in range(9)]
    out = R.save_provenance_warnings(many)
    check("truncates long lists", any("4 more" in line for line in out), str(out[-1:]))


# --- Guard 2: topic scatter --------------------------------------------------

def test_topic_scatter() -> None:
    print("topic-scatter guard")

    with tempfile.TemporaryDirectory() as td:
        topics = Path(td) / "topics"
        (topics / "design").mkdir(parents=True)
        (topics / "design" / "design.flowchart-structures-dashboard.md").write_text("x")
        (topics / "systems").mkdir(parents=True)

        fm = {"title": "Flowchart structures for apps", "tags": ["flowcharts"]}

        out = R.save_topic_scatter_warnings("flowcharts.flowchart-structure-dashboard", fm, content_root=topics)
        check("warns when the top-level is new", any("new top-level topic" in l for l in out), str(out[:1]))
        check("points at the overlapping existing entry",
              any("design.flowchart-structures-dashboard" in l for l in out), str(out))
        check("singularization matches flowcharts to flowchart",
              any("shared terms" in l for l in out), str(out))

        out = R.save_topic_scatter_warnings("design.some-unrelated-thing", {"title": "Kubernetes operator retries"},
                                            content_root=topics)
        check("silent for an existing topic with no overlap", out == [], str(out))

        out = R.save_topic_scatter_warnings("design.flowchart-structures-dashboard-v2", fm, content_root=topics)
        check("does not flag an entry against its own top-level",
              not any("new top-level" in l for l in out), str(out))

        # A new top-level is flagged on its own merits, even with no title vocabulary
        # to match against. Regression guard: the token check must not gate this.
        out = R.save_topic_scatter_warnings("newtop.a", {"title": ""}, content_root=topics)
        check("flags a new top-level even with no title tokens",
              any("new top-level topic" in l for l in out), str(out))
        check("emits no overlap list when there is no vocabulary",
              not any("shared terms" in l for l in out), str(out))

        out = R.save_topic_scatter_warnings("x.y", fm, content_root=Path(td) / "missing")
        check("missing topics root is silent", out == [], str(out))

    # Regression lock: the real 2026-08-31 scatter. Two agents filed near-identical
    # subjects under different top-levels. An earlier tuning pass reached 3% firing
    # while catching NEITHER, so this fixture pins the case the guard exists for.
    # If a future retune drops these, the guard is decorative.
    with tempfile.TemporaryDirectory() as td:
        topics = Path(td) / "topics"
        (topics / "systems").mkdir(parents=True)
        (topics / "systems" / "systems.flowchart-human-ai-agent-guide.md").write_text("x")
        (topics / "flowcharts").mkdir(parents=True)
        (topics / "flowcharts" / "flowcharts.human-ai-agent-systems-guide-2026-08-31.md").write_text("x")

        out = R.save_topic_scatter_warnings(
            "flowcharts.human-ai-agent-systems-guide-2026-08-31", {"title": ""}, content_root=topics)
        check("REGRESSION: catches the real cross-topic duplicate (Terra -> Codex)",
              any("systems.flowchart-human-ai-agent-guide" in l for l in out), str(out))

        out = R.save_topic_scatter_warnings(
            "systems.flowchart-human-ai-agent-guide", {"title": ""}, content_root=topics)
        check("REGRESSION: catches it in the other direction (Codex -> Terra)",
              any("flowcharts.human-ai-agent-systems-guide" in l for l in out), str(out))


# --- Neither guard blocks ----------------------------------------------------

def test_guards_never_block() -> None:
    print("guards are non-blocking")

    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ)
        env["RESEARCH_BASE_DIR"] = td
        entry = Path(td) / "draft.md"
        entry.write_text(
            "---\n"
            "slug: brandnewtopic.some-entry\n"
            "title: Flowchart structures for apps\n"
            "sources:\n"
            "- url: https://a.example/x\n"
            "---\n\n"
            "## TL;DR\n\nBody.\n\n## Notes\n\nMore.\n\n## Raw\n\nSource.\n"
        )
        proc = subprocess.run(
            [sys.executable, str(REPO / "research.py"), "save", "--file", str(entry)],
            capture_output=True, text=True, env=env,
        )
        check("save still exits 0 with both problems present", proc.returncode == 0,
              f"rc={proc.returncode} stderr={proc.stderr[-300:]}")
        check("provenance warning reached stderr", "intake provenance" in proc.stderr, proc.stderr[-200:])
        check("entry was actually written",
              (Path(td) / "topics" / "brandnewtopic" / "brandnewtopic.some-entry.md").is_file())


def main() -> int:
    test_provenance()
    test_topic_scatter()
    test_guards_never_block()
    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("\nsave-guards contract: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
