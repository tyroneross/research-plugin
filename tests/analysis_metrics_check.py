#!/usr/bin/env python3
"""Regression checks for analyze-plan metric scaffolding and the metric engine.

Runs the real CLI end to end against a fixture whose answers are hand-computed,
so a green run means the generated script actually answered the question.
"""
from __future__ import annotations

import csv
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research.py"

# 10 rows. Hand-computed expectations live beside each assertion.
FIXTURE_ROWS = [
    # ts_iso,               surface, subclass,  is_error, latency_ms, result_chars
    ("2026-01-05T10:00:00", "mcp", "sentry", "0", "100", "20"),
    ("2026-01-05T11:00:00", "mcp", "sentry", "1", "200", "40"),
    ("2026-01-06T10:00:00", "mcp", "vercel", "0", "300", "60"),
    ("2026-01-07T10:00:00", "mcp", "vercel", "0", "400", "80"),
    ("2026-01-12T10:00:00", "cli", "git", "0", "500", "100"),
    ("2026-01-12T11:00:00", "cli", "git", "1", "600", "120"),
    ("2026-01-13T10:00:00", "cli", "gh", "1", "700", "140"),
    ("2026-01-14T10:00:00", "cli", "rg", "0", "800", "160"),
    ("2026-01-19T10:00:00", "api", "curl", "0", "900", "180"),
    ("2026-01-20T10:00:00", "api", "curl", "0", "", "200"),
]
HEADERS = ["ts_iso", "surface", "subclass", "is_error", "latency_ms", "result_chars"]

QUESTION = (
    "By surface: call volume, error rate, median/p90 latency_ms and median result_chars; "
    "error-rate trend by week; top 2 subclasses by volume."
)

failures: list[str] = []


def check(label: str, actual: object, expected: object) -> None:
    if actual != expected:
        failures.append(f"{label}: expected {expected!r}, got {actual!r}")


def run(args: list[str], expect_code: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        [sys.executable, str(RESEARCH), *args], capture_output=True, text=True, timeout=120
    )
    if proc.returncode != expect_code:
        failures.append(
            f"`research.py {' '.join(args[:2])}` exited {proc.returncode} (expected {expect_code})\n"
            f"  stdout: {proc.stdout.strip()[:500]}\n  stderr: {proc.stderr.strip()[:500]}"
        )
    return proc


def write_fixture(directory: Path) -> Path:
    path = directory / "tool_calls.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        writer.writerows(FIXTURE_ROWS)
    return path


def group(metric: dict, **key: str) -> dict:
    for g in metric.get("groups") or []:
        if all(g["key"].get(k) == v for k, v in key.items()):
            return g
    detail = f" (metric errored: {metric['error']})" if metric.get("error") else ""
    failures.append(f"metric {metric.get('name')}: no group matching {key}{detail}")
    return {}


def find_metric(results: dict, name: str) -> dict:
    for m in results.get("metrics", []):
        if m.get("name") == name:
            return m
    failures.append(f"results.json has no metric named {name!r} (got {[m.get('name') for m in results.get('metrics', [])]})")
    return {"name": name, "groups": [], "totals": {}}


def check_inference(tmp: Path, csv_path: Path) -> None:
    out_dir = tmp / "inferred"
    run(["analyze-plan", "--input", str(csv_path), "--question", QUESTION, "--out-dir", str(out_dir)])
    plan = json.loads((out_dir / "analysis-plan.json").read_text())

    names = [m["name"] for m in plan["metrics"]]
    check("inferred metric names", names, ["overall", "by_surface", "by_subclass", "by_ts_iso_week"])
    check("inference source", plan["metric_inference"]["source"], "inferred")
    check("top_n carried onto by_subclass", plan["metrics"][2].get("top_n"), 2)

    ops = {a["name"]: a for a in plan["metrics"][1]["aggregations"]}
    check("error_pct inferred", ops.get("error_pct", {}).get("column"), "is_error")
    check("p50 latency inferred", ops.get("p50_latency_ms", {}).get("q"), 0.5)
    check("p90 latency inferred", ops.get("p90_latency_ms", {}).get("q"), 0.9)
    check("p50 result_chars inferred", ops.get("p50_result_chars", {}).get("q"), 0.5)
    check(
        "p90 is not invented for un-asked columns",
        "p90_result_chars" in ops,
        True,  # result_chars is named in the question, so both requested levels apply
    )

    run(["analyze-run", "--plan", str(out_dir / "analysis-plan.yaml")])
    results = json.loads((out_dir / "results.json").read_text())
    check("run status", results["status"], "passed")

    overall = find_metric(results, "overall")
    # 10 rows, 3 errors -> 30.0%
    check("overall count", overall["totals"]["count"], 10)
    check("overall error_pct", overall["totals"]["error_pct"], 30.0)
    # latency present on 9 rows sorted 100..900; nearest-rank p50 = ceil(.5*9)=5th = 500
    check("overall p50 latency", overall["totals"]["p50_latency_ms"], 500)
    # nearest-rank p90 = ceil(.9*9)=9th = 900
    check("overall p90 latency", overall["totals"]["p90_latency_ms"], 900)
    check("latency coverage excludes the blank row", overall["coverage"]["latency_ms"], 9)

    by_surface = find_metric(results, "by_surface")
    check("surface group count", by_surface["group_count"], 3)
    check("surfaces sorted by volume desc", [g["key"]["surface"] for g in by_surface["groups"]], ["mcp", "cli", "api"])
    mcp = group(by_surface, surface="mcp")
    # mcp: 4 calls, 1 error -> 25%; share 4/10 -> 40%
    check("mcp count", mcp.get("count"), 4)
    check("mcp error_pct", mcp.get("error_pct"), 25.0)
    check("mcp share_pct", mcp.get("share_pct"), 40.0)
    # mcp latencies 100,200,300,400 -> p50 = ceil(.5*4)=2nd = 200; p90 = ceil(.9*4)=4th = 400
    check("mcp p50 latency", mcp.get("p50_latency_ms"), 200)
    check("mcp p90 latency", mcp.get("p90_latency_ms"), 400)
    api = group(by_surface, surface="api")
    # api has one blank latency of two rows -> p50 over [900]
    check("api p50 latency ignores blanks", api.get("p50_latency_ms"), 900)

    by_subclass = find_metric(results, "by_subclass")
    # 6 distinct subclasses, truncated to the top 2 by volume (sentry/vercel/git all have 2)
    check("subclass group_count is pre-truncation", by_subclass["group_count"], 6)
    check("subclass truncated_to", by_subclass.get("truncated_to"), 2)
    check("subclass rows shown", len(by_subclass["groups"]), 2)
    check("subclass totals span every row", by_subclass["totals"]["count"], 10)

    weekly = find_metric(results, "by_ts_iso_week")
    check("week buckets", [g["key"]["ts_iso_week"] for g in weekly["groups"]], ["2026-W02", "2026-W03", "2026-W04"])
    # W02 = Jan 5,6,7 -> 4 rows, 1 error
    check("W02 count", weekly["groups"][0]["count"], 4)
    check("W02 error_pct", weekly["groups"][0]["error_pct"], 25.0)
    # W03 = Jan 12,13,14 -> 4 rows, 2 errors
    check("W03 error_pct", weekly["groups"][1]["error_pct"], 50.0)

    audit = (out_dir / "audit.md").read_text()
    for needle in ("## Metrics", "### by_surface", "### by_ts_iso_week"):
        if needle not in audit:
            failures.append(f"audit.md is missing {needle!r}")


def check_explicit_metrics(tmp: Path, csv_path: Path) -> None:
    out_dir = tmp / "explicit"
    spec = [
        {
            "name": "mcp_by_subclass",
            "group_by": ["subclass"],
            "filter": {"column": "surface", "op": "eq", "value": "mcp"},
            "aggregations": [
                {"name": "calls", "op": "count"},
                {"name": "error_pct", "op": "rate", "column": "is_error"},
                {"name": "servers", "op": "count_distinct", "column": "subclass"},
                {"name": "total_chars", "op": "sum", "column": "result_chars"},
                {"name": "max_latency", "op": "max", "column": "latency_ms"},
            ],
            "sort_by": "calls",
        }
    ]
    spec_path = tmp / "metrics.json"
    spec_path.write_text(json.dumps(spec))
    run([
        "analyze-plan", "--input", str(csv_path), "--question", QUESTION,
        "--metrics", str(spec_path), "--out-dir", str(out_dir),
    ])
    plan = json.loads((out_dir / "analysis-plan.json").read_text())
    check("explicit source", plan["metric_inference"]["source"], "explicit")
    check("explicit metric names", [m["name"] for m in plan["metrics"]], ["mcp_by_subclass"])

    run(["analyze-run", "--plan", str(out_dir / "analysis-plan.yaml")])
    results = json.loads((out_dir / "results.json").read_text())
    metric = find_metric(results, "mcp_by_subclass")
    # filter keeps 4 mcp rows: sentry(2, 1 error, chars 20+40), vercel(2, 0 errors, chars 60+80)
    check("filtered row count", metric["rows_scoped"], 4)
    check("filtered groups", [g["key"]["subclass"] for g in metric["groups"]], ["sentry", "vercel"])
    check("sentry error_pct", group(metric, subclass="sentry").get("error_pct"), 50.0)
    check("sentry total_chars", group(metric, subclass="sentry").get("total_chars"), 60)
    check("vercel max_latency", group(metric, subclass="vercel").get("max_latency"), 400)
    check("count_distinct within group", group(metric, subclass="vercel").get("servers"), 1)


def check_inline_and_failure_modes(tmp: Path, csv_path: Path) -> None:
    # Inline JSON is accepted.
    out_dir = tmp / "inline"
    run([
        "analyze-plan", "--input", str(csv_path), "--question", "count by surface",
        "--metrics", '[{"name": "s", "group_by": ["surface"]}]', "--out-dir", str(out_dir),
    ])
    plan = json.loads((out_dir / "analysis-plan.json").read_text())
    check("inline metric parsed", [m["name"] for m in plan["metrics"]], ["s"])

    # A bad op is rejected at plan time, not at run time.
    proc = run([
        "analyze-plan", "--input", str(csv_path), "--question", "q",
        "--metrics", '[{"name": "x", "aggregations": [{"op": "eval"}]}]',
        "--out-dir", str(tmp / "bad-op"),
    ], expect_code=2)
    if "aggregation op 'eval'" not in proc.stderr:
        failures.append(f"bad aggregation op should name the offending op; stderr was: {proc.stderr.strip()[:300]}")

    # A metric naming a column the input lacks fails the run loudly.
    out_dir = tmp / "missing-col"
    run([
        "analyze-plan", "--input", str(csv_path), "--question", "q",
        "--metrics", '[{"name": "ghost", "group_by": ["nope"]}]', "--out-dir", str(out_dir),
    ])
    run(["analyze-run", "--plan", str(out_dir / "analysis-plan.yaml")], expect_code=2)
    results = json.loads((out_dir / "results.json").read_text())
    check("missing column fails validation", results["status"], "validation_failed")
    ghost = find_metric(results, "ghost")
    if "nope" not in str(ghost.get("error", "")):
        failures.append(f"missing-column error should name the column; got {ghost.get('error')!r}")

    # --no-infer-metrics keeps the old profiling-only behavior.
    out_dir = tmp / "no-infer"
    run([
        "analyze-plan", "--input", str(csv_path), "--question", QUESTION,
        "--no-infer-metrics", "--out-dir", str(out_dir),
    ])
    plan = json.loads((out_dir / "analysis-plan.json").read_text())
    check("no-infer yields no metrics", plan["metrics"], [])
    check("no-infer source", plan["metric_inference"]["source"], "disabled")
    run(["analyze-run", "--plan", str(out_dir / "analysis-plan.yaml")])


def check_unmatched_phrases_are_reported(tmp: Path, csv_path: Path) -> None:
    out_dir = tmp / "unmatched"
    proc = run([
        "analyze-plan", "--input", str(csv_path), "--out-dir", str(out_dir),
        "--question", "error rate per mcp-server and per surface",
    ])
    plan = json.loads((out_dir / "analysis-plan.json").read_text())
    check("matched dimension still emitted", [m["name"] for m in plan["metrics"]], ["overall", "by_surface"])
    if "mcp-server" not in plan["metric_inference"]["unmatched"]:
        failures.append(f"unmatched phrase not recorded: {plan['metric_inference']['unmatched']}")
    if "unmatched question phrase" not in proc.stdout:
        failures.append("stdout should surface unmatched phrases so the caller knows to pass --metrics")


def check_sqlite_input(tmp: Path) -> None:
    db = tmp / "calls.sqlite"
    conn = sqlite3.connect(db)
    # `latency_ms` is REAL; `result_chars` is deliberately untyped so the sampled
    # fallback is exercised too.
    conn.execute("CREATE TABLE calls (ts_iso TEXT, surface TEXT, is_error INTEGER, latency_ms REAL, result_chars)")
    conn.executemany("INSERT INTO calls VALUES (?,?,?,?,?)", [
        ("2026-02-02T10:00:00", "mcp", 0, 10.0, 5),
        ("2026-02-02T11:00:00", "mcp", 1, 20.0, 15),
        ("2026-02-03T10:00:00", "cli", 0, 30.0, 25),
        ("2026-02-10T10:00:00", "cli", 1, 40.0, 35),
    ])
    conn.commit()
    conn.close()

    out_dir = tmp / "sqlite"
    run([
        "analyze-plan", "--input", str(db), "--out-dir", str(out_dir),
        "--question",
        "By surface: volume, error rate, p90 latency_ms and median result_chars; error rate by week.",
    ])
    plan = json.loads((out_dir / "analysis-plan.json").read_text())
    check("sqlite metric names", [m["name"] for m in plan["metrics"]], ["overall", "by_surface", "by_ts_iso_week"])
    check("sqlite table carried onto specs", plan["metrics"][1].get("table"), "calls")
    agg_names = {a["name"] for a in plan["metrics"][1]["aggregations"]}
    if "p90_latency_ms" not in agg_names:
        failures.append(f"declared-REAL column should be treated as numeric; aggregations were {sorted(agg_names)}")
    if "p50_result_chars" not in agg_names:
        failures.append(f"untyped-but-numeric column should be treated as numeric; aggregations were {sorted(agg_names)}")

    run(["analyze-run", "--plan", str(out_dir / "analysis-plan.yaml")])
    results = json.loads((out_dir / "results.json").read_text())
    by_surface = find_metric(results, "by_surface")
    mcp = group(by_surface, surface="mcp")
    check("sqlite mcp count", mcp.get("count"), 2)
    check("sqlite mcp error_pct", mcp.get("error_pct"), 50.0)
    # mcp latencies 10,20 -> p90 = ceil(.9*2)=2nd = 20
    check("sqlite mcp p90 latency", mcp.get("p90_latency_ms"), 20)
    check("sqlite mcp p50 result_chars", mcp.get("p50_result_chars"), 5)


def check_high_cardinality_cap(tmp: Path) -> None:
    """An inferred dimension with many values is capped so audit.md stays readable."""
    path = tmp / "wide.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["session_id", "is_error"])
        for i in range(120):
            writer.writerow([f"s{i:04d}", "1" if i % 4 == 0 else "0"])

    out_dir = tmp / "wide-out"
    run(["analyze-plan", "--input", str(path), "--out-dir", str(out_dir),
         "--question", "error rate per session_id"])
    plan = json.loads((out_dir / "analysis-plan.json").read_text())
    by_session = plan["metrics"][1]
    check("high-cardinality dimension capped", by_session.get("top_n"), 50)
    if not any("120 distinct values" in n for n in plan["metric_inference"]["notes"]):
        failures.append(f"cap should be disclosed in notes; got {plan['metric_inference']['notes']}")

    run(["analyze-run", "--plan", str(out_dir / "analysis-plan.yaml")])
    results = json.loads((out_dir / "results.json").read_text())
    metric = find_metric(results, "by_session_id")
    check("true group count still reported", metric.get("group_count"), 120)
    check("rows shown are capped", len(metric.get("groups") or []), 50)
    check("truncation is recorded", metric.get("truncated_to"), 50)
    # 30 of 120 rows have is_error=1
    check("totals cover every row, not just the shown ones", (metric.get("totals") or {}).get("error_pct"), 25.0)


def check_ragged_json_input(tmp: Path) -> None:
    """A column appearing only in late rows must not be reported as missing."""
    path = tmp / "ragged.jsonl"
    lines = [json.dumps({"surface": "cli", "n": i}) for i in range(600)]
    lines.append(json.dumps({"surface": "mcp", "n": 600, "late_column": "7"}))
    path.write_text("\n".join(lines) + "\n")

    out_dir = tmp / "ragged-out"
    run(["analyze-plan", "--input", str(path), "--out-dir", str(out_dir), "--question", "q",
         "--metrics", '[{"name":"late","group_by":["surface"],'
                      '"aggregations":[{"name":"count","op":"count"},'
                      '{"name":"sum_late","op":"sum","column":"late_column"}]}]'])
    run(["analyze-run", "--plan", str(out_dir / "analysis-plan.yaml")])
    results = json.loads((out_dir / "results.json").read_text())
    check("ragged input run status", results["status"], "passed")
    metric = find_metric(results, "late")
    check("late column summed", group(metric, surface="mcp").get("sum_late"), 7)


def main() -> int:
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        csv_path = write_fixture(tmp)
        check_inference(tmp, csv_path)
        check_explicit_metrics(tmp, csv_path)
        check_inline_and_failure_modes(tmp, csv_path)
        check_unmatched_phrases_are_reported(tmp, csv_path)
        check_sqlite_input(tmp)
        check_high_cardinality_cap(tmp)
        check_ragged_json_input(tmp)

    if failures:
        print(f"FAIL — {len(failures)} check(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS — analyze-plan metric scaffolding and metric engine checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
