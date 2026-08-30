from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path

import research


def test_verifier_registry_uses_one_dispatch_contract() -> None:
    for verifier in research.VERIFIERS.values():
        assert len(inspect.signature(verifier).parameters) == 2


def test_optional_symbolic_verifier_is_callable_without_static_dependency() -> None:
    result = research._verify_symbolic({"claim": "1 = 1"}, "unused-entry")

    assert result["verdict"] in {"passed", "inconclusive"}


def test_ordered_pair_has_stable_two_item_shape() -> None:
    assert research._ordered_pair("claim-b", "claim-a") == ("claim-a", "claim-b")


def test_orchestration_timing_does_not_call_staggered_workers_idle() -> None:
    spans = [
        {
            "span_id": "w1", "stage": "worker", "started_at": "2026-01-01T00:00:00+00:00",
            "finished_at": "2026-01-01T00:10:00+00:00", "duration_seconds": 600.0,
        },
        {
            "span_id": "w2", "stage": "worker", "started_at": "2026-01-01T00:05:00+00:00",
            "finished_at": "2026-01-01T00:15:00+00:00", "duration_seconds": 600.0,
        },
        {
            "span_id": "merge", "stage": "merge", "started_at": "2026-01-01T00:15:00+00:00",
            "finished_at": "2026-01-01T00:20:00+00:00", "duration_seconds": 300.0,
        },
    ]

    timing = research._orchestration_timing(spans)

    assert timing["worker_critical_path_seconds"] == 900.0
    assert timing["longest_worker_span_seconds"] == 600.0
    assert timing["worker_dispatch_spread_seconds"] == 300.0
    assert timing["max_concurrent_worker_spans"] == 2
    assert timing["worker_internal_gap_seconds"] == 0.0
    assert timing["worker_to_merge_gap_seconds"] == 0.0
    assert timing["handoff_and_idle_gap_seconds"] == 0.0


def test_eval_check_validates_external_fixture(capsys) -> None:
    root = Path(__file__).parent / "fixtures" / "research-eval"

    status = research.cmd_eval_check(argparse.Namespace(
        root=str(root),
        require_query=["query-one"],
        min_independent_audits=2,
    ))

    report = json.loads(capsys.readouterr().out)
    assert status == 0
    assert report["status"] == "pass"
    assert report["queries"] == ["query-one"]
    assert report["independent_audit_json_files"] == 2
    assert report["distinct_independent_auditors"] == 2
    assert report["package_manifests"] == 1
    assert report["independent_audit_set_hash"].startswith("sha256:")


def test_eval_check_reports_hash_mismatch(tmp_path, capsys) -> None:
    root = tmp_path / "evaluation"
    trial_dir = root / "audit-input" / "candidate"
    raw_dir = trial_dir / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "answer.md").write_text("changed")
    (trial_dir / "trial.json").write_text(json.dumps({
        "query_id": "query-one",
        "arm_id": "candidate",
        "artifacts": {"answer": {"path": "raw/answer.md", "sha256": "0" * 64}},
    }))

    status = research.cmd_eval_check(argparse.Namespace(
        root=str(root),
        require_query=[],
        min_independent_audits=0,
    ))

    report = json.loads(capsys.readouterr().out)
    assert status == 2
    assert report["status"] == "fail"
    assert any("hash mismatch" in error for error in report["errors"])


def test_eval_check_rejects_unhashed_artifacts_and_placeholder_audits(tmp_path, capsys) -> None:
    root = tmp_path / "evaluation"
    trial_dir = root / "audit-input" / "candidate"
    trial_dir.mkdir(parents=True)
    (trial_dir / "answer.md").write_text("answer")
    (trial_dir / "trial.json").write_text(json.dumps({
        "query_id": "query-one",
        "arm_id": "candidate",
        "artifacts": {"answer": {"path": "answer.md"}},
    }))
    audits = root / "audits"
    audits.mkdir()
    (audits / "empty-a.json").write_text("{}")
    (audits / "empty-b.json").write_text("{}")

    status = research.cmd_eval_check(argparse.Namespace(
        root=str(root), require_query=[], min_independent_audits=2,
    ))

    report = json.loads(capsys.readouterr().out)
    assert status == 2
    assert report["independent_audit_json_files"] == 0
    assert any("lacks SHA-256" in error for error in report["errors"])
    assert any("required fields" in error for error in report["errors"])


def test_eval_check_rejects_symlinked_control_file_escape(tmp_path, capsys) -> None:
    root = tmp_path / "evaluation"
    audits = root / "audits"
    audits.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    (audits / "escaped.json").symlink_to(outside)

    status = research.cmd_eval_check(argparse.Namespace(
        root=str(root), require_query=[], min_independent_audits=0,
    ))

    report = json.loads(capsys.readouterr().out)
    assert status == 2
    assert any("may not be a symlink" in error for error in report["errors"])
