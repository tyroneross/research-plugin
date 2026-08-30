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
