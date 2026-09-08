from __future__ import annotations

import json
import hashlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "research.py"
SOURCE_HASH = "sha256:" + "a" * 64
NORMALIZED_HASH = "sha256:" + "b" * 64


def run_cli(tmp_path: Path, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    content = tmp_path / "content"
    index = tmp_path / "index"
    env = os.environ.copy()
    env.update(
        {
            "RESEARCH_BASE_DIR": str(content),
            "RESEARCH_CONTENT_DIR": str(content),
            "RESEARCH_INDEX_DIR": str(index),
        }
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == expected, result.stdout + result.stderr
    return result


def source_manifest(tmp_path: Path, *, run_id: str = "run-test") -> Path:
    path = tmp_path / "source.json"
    path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "url": "https://example.org/research?a=1#fragment",
                "name": "Example research",
                "published_at": "2026-08-01",
                "captured_at": "2026-08-27T10:00:00-07:00",
                "content_hash": SOURCE_HASH,
                "normalized_hash": NORMALIZED_HASH,
                "capture_method": "test-fixture",
                "extractor": "native-text",
                "extractor_version": "1",
                "locator": "section-2",
                "raw_ref": "/external/capture.txt",
            }
        )
    )
    return path


def record_source(tmp_path: Path, *, run_id: str = "run-test") -> str:
    manifest = source_manifest(tmp_path, run_id=run_id)
    result = run_cli(
        tmp_path,
        "source-record",
        "--manifest",
        str(manifest),
        "--run-id",
        run_id,
        "--actor-type",
        "script",
        "--actor-id",
        "fixture",
        "--host",
        "local",
        "--session-id",
        "test-session",
        "--tool-version",
        "test",
    )
    payload = json.loads(result.stdout)
    return payload["observation_id"]


def one_task_contract(run_id: str) -> dict[str, object]:
    return {
        "run_id": run_id,
        "objective": "Test one evidence-bound claim",
        "intent": "Exercise run isolation",
        "outcome": "A validated task result",
        "success_criteria": ["The claim is bound to the intended run"],
        "wrong_answer_consequence": "Stale evidence could be silently accepted",
        "decision_card": {"decision": "Whether to accept the task result", "use": "Validate provenance"},
        "source_policy": {
            "good": ["captured primary evidence"],
            "poor": ["unbound claims"],
            "coverage_lanes": ["primary", "independent", "counter-evidence", "currentness"],
        },
        "hypotheses": [{
            "hypothesis_id": "h1",
            "statement": "The claim is run-bound",
            "falsifiers": ["A stale packet is accepted"],
            "decision_consequence": "Reject the merge",
        }],
        "tasks": [{"task_id": "t1", "section": "evidence", "question": "What supports the claim?", "depends_on": []}],
        "section_contracts": [{"section": "evidence", "completion_criteria": ["One complete observation"]}],
        "merge_strategy": {"single_writer": True, "preserve_contradictions": True},
        "traversal": {
            "max_depth": 2,
            "max_pages": 5,
            "max_bytes": 100000,
            "max_seconds": 30,
            "allowed_domains": ["example.org"],
            "robots_policy": "respect-fail-closed",
        },
    }


def test_append_only_source_and_calculation_receipts(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    observation_id = record_source(tmp_path)
    spec = tmp_path / "calculation.json"
    spec.write_text(
        json.dumps(
            {
                "run_id": "run-test",
                "claim_id": "claim-margin",
                "formula": "part / whole * 100",
                "unit": "percent",
                "denominator": "whole",
                "grain": "one reported period",
                "assumptions": ["part and whole use the same period"],
                "inputs": [
                    {"name": "part", "value": "25", "source_observation_id": observation_id},
                    {"name": "whole", "value": "100", "source_observation_id": observation_id},
                ],
                "checks": [
                    {"name": "expected fixture value", "expression": "result == 25"},
                    {"name": "bounded percent", "expression": "result >= 0"},
                ],
            }
        )
    )
    run_cli(
        tmp_path,
        "calculate",
        "--spec",
        str(spec),
        "--actor-type",
        "script",
        "--actor-id",
        "calculator",
        "--host",
        "local",
    )
    receipts = list((tmp_path / "index" / "calculation-receipts").glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["status"] == "passed"
    assert receipt["result_text"] == "25.00"
    assert receipt["inputs"][0]["source_content_hash"] == SOURCE_HASH

    conn = sqlite3.connect(tmp_path / "index" / ".db.sqlite3")
    with conn:
        try:
            conn.execute("UPDATE calculation_receipts SET status='failed'")
        except sqlite3.IntegrityError as exc:
            assert "append-only" in str(exc)
        else:
            raise AssertionError("calculation receipt update was not rejected")
    conn.close()

    receipt["checks"][0]["passed"] = False
    receipts[0].write_text(json.dumps(receipt))
    doctor = json.loads(run_cli(tmp_path, "doctor", "--json", expected=1).stdout)
    assert not doctor["checks"]["calculation_receipt_integrity"]["passed"]
    assert doctor["checks"]["calculation_receipt_integrity"]["errors"][0]["reason"] == "receipt_hash_mismatch"


def test_ambiguous_calculation_is_inconclusive(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    observation_id = record_source(tmp_path)
    spec = tmp_path / "ambiguous.json"
    spec.write_text(
        json.dumps(
            {
                "run_id": "run-test",
                "claim_id": "claim-ambiguous",
                "formula": "part / whole",
                "unit": "ratio",
                "grain": "unknown",
                "assumptions": [],
                "inputs": [
                    {"name": "part", "value": "1", "source_observation_id": observation_id},
                    {"name": "whole", "value": "0", "source_observation_id": observation_id},
                ],
                "checks": [{"name": "positive", "expression": "result > 0"}],
            }
        )
    )
    run_cli(tmp_path, "calculate", "--spec", str(spec), expected=2)
    receipt = json.loads(next((tmp_path / "index" / "calculation-receipts").glob("*.json")).read_text())
    assert receipt["status"] == "inconclusive"
    assert "missing denominator" in receipt["validation_errors"]


def test_calculation_rejects_non_boolean_check(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    observation_id = record_source(tmp_path)
    spec = tmp_path / "non-boolean-check.json"
    spec.write_text(json.dumps({
        "run_id": "run-test",
        "claim_id": "claim-check",
        "formula": "value * 2",
        "unit": "items",
        "denominator": "not_applicable: direct count",
        "grain": "one fixture",
        "assumptions": [],
        "inputs": [{"name": "value", "value": "2", "source_observation_id": observation_id}],
        "checks": [{"name": "truthy bypass", "expression": "1"}],
    }))
    run_cli(tmp_path, "calculate", "--spec", str(spec), expected=2)
    receipt = json.loads(next((tmp_path / "index" / "calculation-receipts").glob("*.json")).read_text())
    assert receipt["status"] == "inconclusive"
    assert "check must be a boolean comparison" in receipt["failure"]


def test_save_generates_external_indexes_graph_and_valid_chain(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    entry = tmp_path / "entry.md"
    entry.write_text(
        """---
slug: testing.audit-trail
title: Audit trail fixture
topics: [testing, provenance]
projects: [fixture-project]
tags: [audit]
sources:
  - url: https://example.org/article
    name: Example article
    published_at: 2026-08-01
    captured_at: 2026-08-27T10:00:00-07:00
    content_hash: sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
    capture_method: test-fixture
---
## TL;DR

Fixture.

## Notes

Evidence-backed note.

## Raw

Fixture source text.
"""
    )
    run_cli(
        tmp_path,
        "save",
        "--file",
        str(entry),
        "--run-id",
        "run-save",
        "--actor-type",
        "host-agent",
        "--actor-id",
        "test-host",
        "--host",
        "local",
        "--session-id",
        "test-session",
        "--tool-version",
        "test",
    )
    graph = tmp_path / "graph.md"
    run_cli(tmp_path, "graph-export", "--output", str(graph))
    report = json.loads(run_cli(tmp_path, "doctor", "--json").stdout)
    assert report["status"] == "passed"
    assert (tmp_path / "content" / "SOURCE-LEDGER.md").exists()
    assert (tmp_path / "content" / "by-topic.md").read_text().startswith("# Research by Topic")
    assert (tmp_path / "content" / "by-tag.md").read_text().startswith("# Research by Tag")
    assert (tmp_path / "content" / "projects" / "fixture-project" / "INDEX.md").exists()
    assert "hadPrimarySource" in graph.read_text()
    run_cli(tmp_path, "graph-export")
    run_cli(tmp_path, "index")
    assert (tmp_path / "content" / "graphs" / "research-graph.md").exists()
    assert not any(path.name == "SOURCE-LEDGER.md" for path in ROOT.rglob("SOURCE-LEDGER.md"))


def test_run_contract_and_merge_fail_closed(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "run_id": "run-contract",
                "objective": "Test one bounded question",
                "intent": "Exercise orchestration contracts",
                "outcome": "A validated merge",
                "success_criteria": ["All claims are evidence bound"],
                "wrong_answer_consequence": "The merge gate would accept unsupported claims",
                "decision_card": {"decision": "Whether merge validation works", "use": "Choose whether to accept the run"},
                "source_policy": {"good": ["captured primary evidence"], "poor": ["uncited claims"], "coverage_lanes": ["primary", "independent", "counter-evidence", "currentness"]},
                "hypotheses": [{"hypothesis_id": "h1", "statement": "The claim holds", "falsifiers": ["A primary source rejects it"], "decision_consequence": "Reject the claim"}],
                "tasks": [
                    {"task_id": "a", "section": "primary", "question": "What supports it?", "depends_on": []},
                    {"task_id": "b", "section": "counter", "question": "What rejects it?", "depends_on": []},
                ],
                "section_contracts": [
                    {"section": "primary", "completion_criteria": ["Captured support"]},
                    {"section": "counter", "completion_criteria": ["Captured counter-evidence or gap"]},
                ],
                "merge_strategy": {"single_writer": True, "preserve_contradictions": True},
                "traversal": {
                    "max_depth": 2,
                    "max_pages": 10,
                    "max_bytes": 1000000,
                    "max_seconds": 60,
                    "allowed_domains": ["example.org"],
                    "robots_policy": "respect-fail-closed",
                },
            }
        )
    )
    run_cli(tmp_path, "run-validate", "--contract", str(contract))
    init_result = json.loads(run_cli(
        tmp_path,
        "run-init",
        "--contract",
        str(contract),
        "--actor-type",
        "host-agent",
        "--actor-id",
        "coordinator",
        "--host",
        "local",
    ).stdout)
    traversal = tmp_path / "traversal.json"
    traversal.write_text(
        json.dumps(
            {
                "run_id": "run-contract",
                "links": [
                    {"url": "https://example.org/methods", "depth": 2, "robots_allowed": True, "bytes": 100, "elapsed_ms": 5},
                    {"url": "http://127.0.0.1/private", "depth": 2, "robots_allowed": True},
                    {"url": "https://example.org/too-deep", "depth": 3, "robots_allowed": True},
                    {"url": "https://user:secret@example.org/private", "depth": 2, "robots_allowed": True},
                ],
            }
        )
    )
    traversal_result = json.loads(
        run_cli(tmp_path, "traversal-record", "--manifest", str(traversal), "--run-id", "run-contract").stdout
    )
    assert [item["decision"] for item in traversal_result["records"]] == ["queued", "rejected", "rejected", "rejected"]
    assert traversal_result["records"][1]["reason"] == "private_or_local_destination"
    assert traversal_result["records"][2]["reason"] == "depth_limit"
    assert traversal_result["records"][3]["reason"] == "credential_bearing_url"
    conn = sqlite3.connect(tmp_path / "index" / ".db.sqlite3")
    persisted_link = conn.execute("SELECT displayed_url, resolved_url, metadata_json FROM traversal_links WHERE reason='credential_bearing_url'").fetchone()
    conn.close()
    assert "secret" not in " ".join(persisted_link)
    result_a = tmp_path / "a.json"
    result_b = tmp_path / "b.json"
    result_a.write_text(
        json.dumps(
            {
                "run_id": "run-contract",
                "initialized_contract_hash": init_result["contract_hash"],
                "task_id": "a",
                "claims": [
                    {
                        "claim_id": "c1",
                        "statement": "A missing quantitative claim",
                        "claim_kind": "quantitative",
                        "evidence_observation_ids": ["obs-missing"],
                        "calculation_receipt_id": None,
                        "contradicts": ["c2"],
                    }
                ],
                "source_observation_ids": ["obs-missing"],
                "reused_observation_ids": [],
                "limitations": [],
            }
        )
    )
    result_b.write_text(
        json.dumps(
            {
                "run_id": "run-contract",
                "initialized_contract_hash": init_result["contract_hash"],
                "task_id": "b",
                "claims": [
                    {"claim_id": "c2", "statement": "A conflicting claim", "claim_kind": "factual", "evidence_observation_ids": ["obs-other"], "contradicts": ["c1"]}
                ],
                "source_observation_ids": ["obs-other"],
                "reused_observation_ids": [],
                "limitations": [],
            }
        )
    )
    merged = run_cli(
        tmp_path,
        "run-merge",
        "--contract",
        str(contract),
        "--result",
        str(result_a),
        "--result",
        str(result_b),
        expected=2,
    )
    payload = json.loads(merged.stdout)
    assert payload["status"] == "invalid"
    assert any("passed calculation receipt" in error for error in payload["errors"])
    assert any("unreconciled contradiction" in error for error in payload["errors"])

    mutated_contract = json.loads(contract.read_text())
    mutated_contract["objective"] = "Changed after initialization"
    mutated = tmp_path / "mutated-contract.json"
    mutated.write_text(json.dumps(mutated_contract))
    tampered = run_cli(
        tmp_path,
        "run-merge",
        "--contract",
        str(mutated),
        "--result",
        str(result_a),
        "--result",
        str(result_b),
        expected=2,
    )
    assert "differs from the initialized contract" in tampered.stdout

    duplicate_workers = run_cli(
        tmp_path,
        "run-merge",
        "--contract",
        str(contract),
        "--result",
        str(result_a),
        "--result",
        str(result_a),
        "--result",
        str(result_b),
        expected=2,
    )
    assert "duplicate task results" in duplicate_workers.stdout


def test_run_contract_rejects_type_and_budget_bypasses(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    contract = tmp_path / "bad-contract.json"
    contract.write_text(
        json.dumps(
            {
                "objective": "Bad contract",
                "intent": "Adversarial validation",
                "outcome": "Must fail",
                "source_policy": "all sources",
                "hypotheses": "one hypothesis",
                "tasks": "one task",
                "merge_strategy": "merge everything",
                "traversal": {
                    "max_depth": 2,
                    "max_pages": -1,
                    "max_bytes": -1,
                    "max_seconds": -1,
                    "allowed_domains": "example.org",
                    "robots_policy": "respect-fail-closed",
                },
            }
        )
    )
    result = run_cli(tmp_path, "run-validate", "--contract", str(contract), expected=2)
    payload = json.loads(result.stdout)
    assert payload["status"] == "invalid"
    assert "source_policy must be an object" in payload["errors"]
    assert "traversal.max_pages must be a positive integer" in payload["errors"]
    assert "traversal.allowed_domains must be a non-empty list of domain names" in payload["errors"]


def test_valid_merge_persists_claim_graph_discrepancy_and_trust(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    contract = tmp_path / "valid-contract.json"
    contract.write_text(
        json.dumps(
            {
                "run_id": "run-valid",
                "objective": "Reconcile two claims",
                "intent": "Exercise graph persistence",
                "outcome": "A preserved discrepancy",
                "success_criteria": ["Both claims and the discrepancy persist"],
                "wrong_answer_consequence": "A contradiction could be silently lost",
                "decision_card": {"decision": "Whether to accept the metric", "use": "Review both evidence bases"},
                "source_policy": {"good": ["captured primary evidence"], "poor": ["uncited claims"], "coverage_lanes": ["primary", "independent", "counter-evidence", "currentness"]},
                "hypotheses": [{"hypothesis_id": "h1", "statement": "The metric is 25 percent", "falsifiers": ["A source-linked calculation differs"], "decision_consequence": "Preserve the discrepancy"}],
                "tasks": [
                    {"task_id": "a", "section": "primary", "question": "What is the metric?", "depends_on": []},
                    {"task_id": "b", "section": "counter", "question": "What alternative basis exists?", "depends_on": []},
                ],
                "section_contracts": [
                    {"section": "primary", "completion_criteria": ["Verified calculation"]},
                    {"section": "counter", "completion_criteria": ["Captured alternative"]},
                ],
                "merge_strategy": {"single_writer": True, "preserve_contradictions": True},
                "traversal": {
                    "max_depth": 2,
                    "max_pages": 10,
                    "max_bytes": 1000000,
                    "max_seconds": 60,
                    "allowed_domains": ["example.org"],
                    "robots_policy": "respect-fail-closed",
                },
            }
        )
    )
    init_result = json.loads(run_cli(
        tmp_path,
        "run-init",
        "--contract",
        str(contract),
        "--actor-type",
        "host-agent",
        "--actor-id",
        "coordinator",
        "--host",
        "local",
    ).stdout)
    observation_id = record_source(tmp_path, run_id="run-valid")
    calculation = tmp_path / "valid-calculation.json"
    calculation.write_text(
        json.dumps(
            {
                "run_id": "run-valid",
                "claim_id": "c1",
                "formula": "part / whole * 100",
                "unit": "percent",
                "denominator": "whole",
                "grain": "one period",
                "assumptions": [],
                "inputs": [
                    {"name": "part", "value": "25", "source_observation_id": observation_id},
                    {"name": "whole", "value": "100", "source_observation_id": observation_id},
                ],
                "checks": [{"name": "expected", "expression": "result == 25"}],
            }
        )
    )
    run_cli(tmp_path, "calculate", "--spec", str(calculation))
    receipt = json.loads(next((tmp_path / "index" / "calculation-receipts").glob("*.json")).read_text())
    result_a = tmp_path / "valid-a.json"
    result_b = tmp_path / "valid-b.json"
    result_a.write_text(
        json.dumps(
            {
                "run_id": "run-valid",
                "initialized_contract_hash": init_result["contract_hash"],
                "task_id": "a",
                "claims": [
                    {
                        "claim_id": "c1",
                        "statement": "The metric is 25 percent",
                        "claim_kind": "quantitative",
                        "evidence_observation_ids": [observation_id],
                        "calculation_receipt_id": receipt["receipt_id"],
                        "contradicts": ["c2"],
                    }
                ],
                "source_observation_ids": [observation_id],
                "reused_observation_ids": [],
                "limitations": [],
            }
        )
    )
    result_b.write_text(
        json.dumps(
            {
                "run_id": "run-valid",
                "initialized_contract_hash": init_result["contract_hash"],
                "task_id": "b",
                "claims": [
                    {
                        "claim_id": "c2",
                        "statement": "A different basis gives another value",
                        "claim_kind": "factual",
                        "evidence_observation_ids": [observation_id],
                        "contradicts": ["c1"],
                    }
                ],
                "source_observation_ids": [observation_id],
                "reused_observation_ids": [],
                "limitations": [],
            }
        )
    )
    reconciliation = tmp_path / "reconciliation.json"
    reconciliation.write_text(
        json.dumps(
            {
                "run_id": "run-valid",
                "initialized_contract_hash": init_result["contract_hash"],
                "reconciliations": [
                    {"left_claim_id": "c1", "right_claim_id": "c2", "status": "preserved", "type": "basis_difference"}
                ],
            }
        )
    )
    bad_reconciliation = tmp_path / "bad-reconciliation.json"
    bad_payload = json.loads(reconciliation.read_text())
    bad_payload["initialized_contract_hash"] = "sha256:" + "0" * 64
    bad_reconciliation.write_text(json.dumps(bad_payload))
    bad_merge = run_cli(
        tmp_path,
        "run-merge",
        "--contract",
        str(contract),
        "--result",
        str(result_a),
        "--result",
        str(result_b),
        "--reconciliation",
        str(bad_reconciliation),
        expected=2,
    )
    assert "reconciliation manifest contract hash does not match" in bad_merge.stdout
    merge_result = run_cli(
        tmp_path,
        "run-merge",
        "--contract",
        str(contract),
        "--result",
        str(result_a),
        "--result",
        str(result_b),
        "--reconciliation",
        str(reconciliation),
    )
    merged_payload = json.loads(merge_result.stdout)
    result_record = next(item for item in merged_payload["input_provenance"]["results"] if item["task_id"] == "a")
    snapshot_path = Path(result_record["snapshot_path"])
    preserved_bytes = snapshot_path.read_bytes()
    assert "c1" in preserved_bytes.decode()
    result_a.write_text("{}")
    assert snapshot_path.read_bytes() == preserved_bytes
    assert "sha256:" + hashlib.sha256(preserved_bytes).hexdigest() == result_record["content_hash"]
    assert merged_payload["input_provenance"]["reconciliation"]["content_hash"].startswith("sha256:")
    trust = tmp_path / "trust.json"
    trust.write_text(
        json.dumps(
            {
                "run_id": "run-valid",
                "topic_key": "testing",
                "subject": {"kind": "source", "canonical_key": "https://example.org/research?a=1", "label": "Example research"},
                "observations": [
                    {
                        "dimension": "uncertainty_calibration",
                        "rating": "high",
                        "rationale": "The fixture states its scope",
                        "evidence_observation_id": observation_id,
                    }
                ],
            }
        )
    )
    run_cli(tmp_path, "trust-record", "--manifest", str(trust), "--run-id", "run-valid")
    graph = tmp_path / "graph.json"
    run_cli(tmp_path, "graph-export", "--run-id", "run-valid", "--format", "json", "--output", str(graph))
    payload = json.loads(graph.read_text())
    assert payload["discrepancies"][0]["status"] == "preserved"
    assert payload["trust_observations"][0]["dimension"] == "uncertainty_calibration"
    assert any(edge["predicate"] == "contradicts" for edge in payload["edges"])
    assert payload["source_observations"][0]["content_hash"] == SOURCE_HASH
    assert payload["source_observations"][0]["captured_at"] == "2026-08-27T10:00:00-07:00"
    snapshot_path.write_text("{}")
    doctor = json.loads(run_cli(tmp_path, "doctor", "--json", expected=1).stdout)
    assert {item["reason"] for item in doctor["checks"]["merge_attempt_integrity"]["errors"]} == {"merge_input_hash_mismatch"}


def test_claim_ids_are_namespaced_by_run(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    for run_id in ("run-one", "run-two"):
        observation_id = record_source(tmp_path, run_id=run_id)
        spec = tmp_path / f"{run_id}.json"
        spec.write_text(json.dumps({
            "run_id": run_id,
            "claim_id": "c1",
            "formula": "value + 1",
            "unit": "items",
            "denominator": "not_applicable: direct count",
            "grain": "one fixture",
            "assumptions": [],
            "inputs": [{"name": "value", "value": "1", "source_observation_id": observation_id}],
            "checks": [{"name": "expected", "expression": "result == 2"}],
        }))
        run_cli(tmp_path, "calculate", "--spec", str(spec))
    conn = sqlite3.connect(tmp_path / "index" / ".db.sqlite3")
    keys = {row[0] for row in conn.execute("SELECT canonical_key FROM graph_entities WHERE kind='claim'")}
    conn.close()
    assert {"run-one:c1", "run-two:c1"}.issubset(keys)


def test_legacy_source_import_is_idempotent_and_preserves_unknowns(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    topic_dir = tmp_path / "content" / "topics" / "legacy"
    topic_dir.mkdir(parents=True)
    entry_path = topic_dir / "legacy.entry.md"
    entry_path.write_text("---\nslug: legacy.entry\ntitle: Legacy entry\ntopics: [legacy]\n---\n## TL;DR\n\nLegacy.\n")
    conn = sqlite3.connect(tmp_path / "index" / ".db.sqlite3")
    conn.execute(
        """INSERT INTO entries
           (slug, path, title, topics, projects, tags, sources, status, reviewed, tldr, notes, raw)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "legacy.entry", str(entry_path), "Legacy entry", '["legacy"]', "[]", "[]",
            '["https://example.org/legacy"]', "evergreen", "2026-08-01", "Legacy.", "", "",
        ),
    )
    conn.commit()
    conn.close()
    dry = json.loads(run_cli(tmp_path, "legacy-source-import").stdout)
    assert dry["mode"] == "dry-run" and dry["planned_entries"] == 1
    applied = json.loads(run_cli(tmp_path, "legacy-source-import", "--apply").stdout)
    assert applied["imported_observations"] == 1
    second = json.loads(run_cli(tmp_path, "legacy-source-import", "--apply").stdout)
    assert second["imported_observations"] == 0
    conn = sqlite3.connect(tmp_path / "index" / ".db.sqlite3")
    conn.execute(
        "UPDATE entries SET sources=? WHERE slug='legacy.entry'",
        ('["https://example.org/legacy", "https://example.org/legacy-two"]',),
    )
    conn.commit()
    conn.close()
    partial = json.loads(run_cli(tmp_path, "legacy-source-import", "--apply").stdout)
    assert partial["imported_observations"] == 1
    conn = sqlite3.connect(tmp_path / "index" / ".db.sqlite3")
    conn.row_factory = sqlite3.Row
    observation = conn.execute("SELECT * FROM source_observations ORDER BY source_id LIMIT 1").fetchone()
    conn.close()
    assert observation["captured_at"] == "0001-01-01T00:00:00Z"
    assert observation["status"] == "legacy-provenance-unknown"
    metadata = json.loads(observation["metadata_json"])
    assert metadata["captured_at_unknown_reason"]
    doctor = json.loads(run_cli(tmp_path, "doctor", "--json", expected=1).stdout)
    assert not doctor["checks"]["source_history"]["passed"]
    assert "https://example.org/legacy" in (tmp_path / "content" / "SOURCE-LEDGER.md").read_text()


def test_source_hash_validation_rejects_malformed_identity(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    manifest = source_manifest(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["content_hash"] = "abc"
    manifest.write_text(json.dumps(payload))
    result = run_cli(tmp_path, "source-record", "--manifest", str(manifest), expected=2)
    assert "sha256:<64 lowercase hex>" in result.stderr

    payload["content_hash"] = SOURCE_HASH
    payload["captured_at"] = "unknown"
    manifest.write_text(json.dumps(payload))
    date_result = run_cli(tmp_path, "source-record", "--manifest", str(manifest), expected=2)
    assert "captured_at must be ISO-8601" in date_result.stderr


def test_invalid_correction_does_not_leave_receipt_orphan(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    observation_id = record_source(tmp_path)
    spec = tmp_path / "bad-correction.json"
    spec.write_text(json.dumps({
        "run_id": "run-test",
        "claim_id": "claim-correction",
        "correction_of_receipt_id": "calc-does-not-exist",
        "formula": "value + 1",
        "unit": "items",
        "denominator": "not_applicable: direct count",
        "grain": "one fixture",
        "assumptions": [],
        "inputs": [{"name": "value", "value": "1", "source_observation_id": observation_id}],
        "checks": [{"name": "expected", "expression": "result == 2"}],
    }))
    run_cli(tmp_path, "calculate", "--spec", str(spec), expected=2)
    assert not list((tmp_path / "index" / "calculation-receipts").glob("*.json"))

    orphan_dir = tmp_path / "index" / "calculation-receipts"
    orphan_dir.mkdir(parents=True, exist_ok=True)
    (orphan_dir / "orphan.json").write_text("{}")
    doctor = json.loads(run_cli(tmp_path, "doctor", "--json", expected=1).stdout)
    assert {item["reason"] for item in doctor["checks"]["calculation_receipt_integrity"]["errors"]} == {"unindexed_receipt_file"}


def test_event_uses_operation_actor_snapshot_not_run_creator(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    contract_path = tmp_path / "actor-contract.json"
    contract_path.write_text(json.dumps(one_task_contract("run-actors")))
    run_cli(
        tmp_path,
        "run-init",
        "--contract",
        str(contract_path),
        "--actor-type",
        "host-agent",
        "--actor-id",
        "coordinator",
        "--host",
        "local",
        "--session-id",
        "session-a",
        "--tool-version",
        "coordinator-v1",
    )
    manifest = source_manifest(tmp_path, run_id="run-actors")
    run_cli(
        tmp_path,
        "source-record",
        "--manifest",
        str(manifest),
        "--run-id",
        "run-actors",
        "--actor-type",
        "worker-agent",
        "--actor-id",
        "worker-one",
        "--host",
        "local-worker",
        "--session-id",
        "session-b",
        "--tool-version",
        "worker-v2",
    )
    conn = sqlite3.connect(tmp_path / "index" / ".db.sqlite3")
    conn.row_factory = sqlite3.Row
    created = conn.execute("SELECT * FROM audit_events WHERE event_type='run.created'").fetchone()
    observed = conn.execute("SELECT * FROM audit_events WHERE event_type='source.observed'").fetchone()
    conn.close()
    assert (created["actor_id"], created["session_id"], created["tool_version"]) == ("coordinator", "session-a", "coordinator-v1")
    assert (observed["actor_id"], observed["session_id"], observed["tool_version"]) == ("worker-one", "session-b", "worker-v2")


def test_merge_rejects_stale_packets_and_requires_declared_cross_run_reuse(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    init_results: dict[str, dict[str, object]] = {}
    for run_id in ("run-origin", "run-target"):
        contract_path = tmp_path / f"{run_id}.contract.json"
        contract_path.write_text(json.dumps(one_task_contract(run_id)))
        init_results[run_id] = json.loads(run_cli(
            tmp_path, "run-init", "--contract", str(contract_path),
            "--actor-type", "host-agent", "--actor-id", "coordinator", "--host", "local",
        ).stdout)
    observation_id = record_source(tmp_path, run_id="run-origin")
    target_contract = tmp_path / "run-target.contract.json"

    def write_result(name: str, *, run_id: str, contract_hash: str, reused: list[str], contradicts: list[str]) -> Path:
        path = tmp_path / name
        path.write_text(json.dumps({
            "run_id": run_id,
            "initialized_contract_hash": contract_hash,
            "task_id": "t1",
            "claims": [{
                "claim_id": "c1",
                "statement": "The fixture source exists",
                "claim_kind": "factual",
                "evidence_observation_ids": [observation_id],
                "contradicts": contradicts,
            }],
            "source_observation_ids": [observation_id],
            "reused_observation_ids": reused,
            "limitations": [],
        }))
        return path

    stale = write_result(
        "stale.json",
        run_id="run-origin",
        contract_hash=str(init_results["run-origin"]["contract_hash"]),
        reused=[],
        contradicts=[],
    )
    stale_merge = run_cli(tmp_path, "run-merge", "--contract", str(target_contract), "--result", str(stale), expected=2)
    assert "result run_id does not match" in stale_merge.stdout
    assert "result contract hash does not match" in stale_merge.stdout

    undeclared = write_result(
        "undeclared.json",
        run_id="run-target",
        contract_hash=str(init_results["run-target"]["contract_hash"]),
        reused=[],
        contradicts=[],
    )
    undeclared_merge = run_cli(tmp_path, "run-merge", "--contract", str(target_contract), "--result", str(undeclared), expected=2)
    assert "cross-run evidence must be declared" in undeclared_merge.stdout

    missing_target = write_result(
        "missing-target.json",
        run_id="run-target",
        contract_hash=str(init_results["run-target"]["contract_hash"]),
        reused=[observation_id],
        contradicts=["missing-claim"],
    )
    contradiction_merge = run_cli(tmp_path, "run-merge", "--contract", str(target_contract), "--result", str(missing_target), expected=2)
    assert "contradicts unknown claim missing-claim" in contradiction_merge.stdout

    declared = write_result(
        "declared.json",
        run_id="run-target",
        contract_hash=str(init_results["run-target"]["contract_hash"]),
        reused=[observation_id],
        contradicts=[],
    )
    run_cli(tmp_path, "run-merge", "--contract", str(target_contract), "--result", str(declared))
    conn = sqlite3.connect(tmp_path / "index" / ".db.sqlite3")
    reused_edges = conn.execute("SELECT COUNT(*) FROM graph_edges WHERE run_id='run-target' AND predicate='reusedObservation'").fetchone()[0]
    conn.close()
    assert reused_edges == 1


def test_skill_is_vendor_neutral_and_local_ocr_is_optional() -> None:
    skill = (ROOT / "skills" / "research-orchestrator" / "SKILL.md").read_text().lower()
    frontmatter = skill.split("---", 2)[1]
    assert "claude" not in frontmatter
    assert "anthropic" not in frontmatter
    assert "openai" not in frontmatter
    assert "host's native agent mechanism" in skill
    assert (ROOT / "skills" / "research-orchestrator" / "scripts" / "local_ocr.swift").exists()
    runtime = (ROOT / "research.py").read_text().lower()
    assert "claude's read" not in runtime
    assert "have claude" not in runtime
    assert "[claude:" not in runtime


def test_run_stage_metrics_capture_fanout_and_merge_overhead(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    contract_path = tmp_path / "timed.contract.json"
    contract = one_task_contract("run-timed")
    contract["tasks"] = [
        {"task_id": "t1", "section": "evidence-a", "question": "What supports A?", "depends_on": []},
        {"task_id": "t2", "section": "evidence-b", "question": "What supports B?", "depends_on": []},
    ]
    contract["section_contracts"] = [
        {"section": "evidence-a", "completion_criteria": ["One complete observation"]},
        {"section": "evidence-b", "completion_criteria": ["One complete observation"]},
    ]
    contract_path.write_text(json.dumps(contract))
    run_cli(tmp_path, "run-init", "--contract", str(contract_path))

    workers = (("worker-1", "luna-1", "t1"), ("worker-2", "terra-1", "t2"))
    for span_id, worker_id, task_id in workers:
        run_cli(
            tmp_path,
            "run-stage",
            "--run-id", "run-timed",
            "--span-id", span_id,
            "--stage", "worker",
            "--action", "start",
            "--worker-id", worker_id,
            "--task-id", task_id,
        )
    for span_id, worker_id, task_id, input_tokens in (
        ("worker-1", "luna-1", "t1", 10),
        ("worker-2", "terra-1", "t2", 20),
    ):
        receipt = tmp_path / f"{span_id}.json"
        receipt.write_text(json.dumps({"span_id": span_id, "result": "complete"}))
        run_cli(
            tmp_path,
            "run-stage",
            "--run-id", "run-timed",
            "--span-id", span_id,
            "--stage", "worker",
            "--action", "finish",
            "--worker-id", worker_id,
            "--task-id", task_id,
            "--receipt-path", str(receipt),
            "--metrics", json.dumps({"input_tokens": input_tokens}),
        )
    run_cli(
        tmp_path,
        "run-stage",
        "--run-id", "run-timed",
        "--span-id", "merge-1",
        "--stage", "merge",
        "--action", "start",
    )
    run_cli(
        tmp_path,
        "run-stage",
        "--run-id", "run-timed",
        "--span-id", "merge-1",
        "--stage", "merge",
        "--action", "finish",
        "--metrics", json.dumps({"output_tokens": 5, "tool_calls": 2}),
    )

    report = json.loads(run_cli(tmp_path, "run-metrics", "--run-id", "run-timed").stdout)
    assert report["status"] == "complete"
    assert report["span_count"] == 3
    assert report["worker_stage_wall_seconds"] > 0
    assert report["worker_parallelism_ratio"] > 1
    assert report["max_concurrent_worker_spans"] == 2
    assert report["merge_wall_seconds"] > 0
    assert report["worker_to_merge_gap_seconds"] >= 0
    assert report["concurrency_evidence"] == "artifact_bound_declared_span_overlap"
    assert report["reported_metric_totals"] == {
        "input_tokens": "30",
        "output_tokens": "5",
        "tool_calls": "2",
    }
    assert report["longest_stage_by_total"] == "worker"


def test_run_stage_rejects_unpaired_or_mismatched_finish(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    contract_path = tmp_path / "timed.contract.json"
    contract_path.write_text(json.dumps(one_task_contract("run-timed")))
    run_cli(tmp_path, "run-init", "--contract", str(contract_path))
    receipt = tmp_path / "worker.json"
    receipt.write_text('{"result":"complete"}')

    missing = run_cli(
        tmp_path,
        "run-stage",
        "--run-id", "run-timed",
        "--span-id", "missing",
        "--stage", "worker",
        "--action", "finish",
        "--worker-id", "luna-1",
        "--task-id", "t1",
        "--receipt-path", str(receipt),
        expected=2,
    )
    assert "no start event" in missing.stderr

    run_cli(
        tmp_path,
        "run-stage",
        "--run-id", "run-timed",
        "--span-id", "worker-1",
        "--stage", "worker",
        "--action", "start",
        "--worker-id", "luna-1",
        "--task-id", "t1",
    )
    mismatch = run_cli(
        tmp_path,
        "run-stage",
        "--run-id", "run-timed",
        "--span-id", "worker-1",
        "--stage", "worker",
        "--action", "finish",
        "--worker-id", "terra-1",
        "--task-id", "t1",
        "--receipt-path", str(receipt),
        expected=2,
    )
    assert "does not match" in mismatch.stderr

    no_receipt = run_cli(
        tmp_path,
        "run-stage",
        "--run-id", "run-timed",
        "--span-id", "worker-1",
        "--stage", "worker",
        "--action", "finish",
        "--worker-id", "luna-1",
        "--task-id", "t1",
        expected=2,
    )
    assert "requires --receipt-path" in no_receipt.stderr

    run_cli(
        tmp_path, "run-stage", "--run-id", "run-timed", "--span-id", "merge-identity",
        "--stage", "merge", "--action", "start",
    )
    retroactive_worker = run_cli(
        tmp_path, "run-stage", "--run-id", "run-timed", "--span-id", "merge-identity",
        "--stage", "merge", "--action", "finish", "--worker-id", "retroactive-worker",
        expected=2,
    )
    assert "valid only" in retroactive_worker.stderr

    undeclared = run_cli(
        tmp_path, "run-stage", "--run-id", "run-timed", "--span-id", "undeclared-task",
        "--stage", "worker", "--action", "start", "--worker-id", "luna-2", "--task-id", "missing",
        expected=2,
    )
    assert "not declared" in undeclared.stderr


def test_run_stage_serializes_duplicate_span_starts(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    contract_path = tmp_path / "timed.contract.json"
    contract_path.write_text(json.dumps(one_task_contract("run-timed")))
    run_cli(tmp_path, "run-init", "--contract", str(contract_path))
    env = os.environ.copy()
    env.update({
        "RESEARCH_BASE_DIR": str(tmp_path / "content"),
        "RESEARCH_CONTENT_DIR": str(tmp_path / "content"),
        "RESEARCH_INDEX_DIR": str(tmp_path / "index"),
    })
    command = [
        sys.executable, str(SCRIPT), "run-stage", "--run-id", "run-timed",
        "--span-id", "same-span", "--stage", "worker", "--action", "start",
        "--worker-id", "worker-a", "--task-id", "t1",
    ]
    processes = [
        subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for _ in range(2)
    ]
    results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]

    assert sorted(result[2] for result in results) == [0, 2]
    assert any("already exists" in result[1] for result in results)


def test_run_stage_rejects_worker_on_ad_hoc_run_without_contract(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    record_source(tmp_path, run_id="run-adhoc")

    result = run_cli(
        tmp_path, "run-stage", "--run-id", "run-adhoc", "--span-id", "worker-adhoc",
        "--stage", "worker", "--action", "start", "--worker-id", "worker-a", "--task-id", "made-up",
        expected=2,
    )

    assert "initialized from a task contract" in result.stderr


def test_doctor_plan_is_deterministic_and_does_not_apply_repairs(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    empty_plan = json.loads(run_cli(tmp_path, "doctor-plan").stdout)
    assert empty_plan["action_count"] == 0
    assert empty_plan["writes_performed"] is False

    malformed = tmp_path / "content" / "topics" / "legacy" / "missing-slug.md"
    malformed.parent.mkdir(parents=True)
    original = "---\ntitle: Missing slug\n---\nEvidence stays unchanged.\n"
    malformed.write_text(original)
    first = json.loads(run_cli(tmp_path, "doctor-plan", "--sample-limit", "1", expected=1).stdout)
    second = json.loads(run_cli(tmp_path, "doctor-plan", "--sample-limit", "1", expected=1).stdout)

    assert first == second
    assert first["mode"] == "plan-only"
    assert first["plan_hash"].startswith("sha256:")
    categories = {action["category"] for action in first["actions"]}
    assert "frontmatter" in categories
    assert all(action["review_required"] for action in first["actions"])
    assert malformed.read_text() == original


def test_doctor_plan_rejects_negative_sample_limit(tmp_path: Path) -> None:
    run_cli(tmp_path, "init")
    result = run_cli(tmp_path, "doctor-plan", "--sample-limit", "-1", expected=2)
    assert "zero or greater" in result.stderr


def test_doctor_plan_refuses_uninitialized_corpus_without_writing(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "doctor-plan", expected=2)
    assert "not initialized" in result.stderr
    assert not (tmp_path / "content").exists()
    assert not (tmp_path / "index").exists()


def test_graph_connects_values_formulas_sources_and_corrections(tmp_path: Path) -> None:
    observation = record_source(tmp_path)
    spec = {
        'run_id': 'run-test', 'claim_id': 'savings', 'formula': 'before - after',
        'unit': 'USD', 'denominator': 'not_applicable: difference', 'grain': 'annual cost',
        'assumptions': ['equal scope'],
        'inputs': [
            {'name': 'before', 'value': '120', 'unit': 'USD', 'source_observation_id': observation},
            {'name': 'after', 'value': '90', 'unit': 'USD', 'source_observation_id': observation},
        ],
        'checks': [{'name': 'fixture', 'expression': 'result == 30'}],
    }
    path = tmp_path / 'calculation.json'
    path.write_text(json.dumps(spec))
    run_cli(tmp_path, 'calculate', '--spec', str(path))
    receipt = json.loads(next((tmp_path / 'index/calculation-receipts').glob('*.json')).read_text())
    spec['correction_of_receipt_id'] = receipt['receipt_id']
    spec['inputs'][1]['value'] = '80'
    # A deliberately failing check must remain failed in the graph, not imply support.
    path.write_text(json.dumps(spec))
    run_cli(tmp_path, 'calculate', '--spec', str(path), expected=2)
    graph = tmp_path / 'graph.json'
    run_cli(tmp_path, 'graph-export', '--run-id', 'run-test', '--format', 'json', '--output', str(graph))
    data = json.loads(graph.read_text())
    assert len(data['calculations']) == 2
    persisted_calc_ids = {e['entity_id'] for e in data['entities'] if e['kind'] == 'calculation'}
    assert {e['subject_id'] for e in data['edges'] if e['predicate'] == 'usedValue'} <= persisted_calc_ids
    assert {c['status'] for c in data['calculations']} == {'passed', 'failed'}
    assert {'usedValue', 'wasDerivedFrom', 'corrects'} <= {e['predicate'] for e in data['edges']}
    assert any('40 USD [failed]' in label for label in data['numeric_labels'].values())
    assert any('before = 120 USD' in label for label in data['numeric_labels'].values())
    mermaid = tmp_path / 'graph.md'
    run_cli(tmp_path, 'graph-export', '--run-id', 'run-test', '--output', str(mermaid))
    assert 'formula: before - after' in mermaid.read_text()
    assert '40 USD [failed]' in mermaid.read_text()
    assert 'annual cost' in mermaid.read_text()
    run_cli(tmp_path, 'graph-export', '--run-id', 'other-run', '--format', 'json', '--output', str(graph))
    assert json.loads(graph.read_text())['calculations'] == []
    # Export enriches existing receipts without adding graph rows to the database.
    conn = sqlite3.connect(tmp_path / 'index/.db.sqlite3')
    assert conn.execute("SELECT count(*) FROM graph_entities WHERE kind='quantity'").fetchone()[0] == 0
    conn.close()


def test_mixed_evidence_connections_preserve_basis_and_assertion(tmp_path: Path) -> None:
    run_id = 'mixed-evidence'
    contract = tmp_path / 'contract.json'
    contract.write_text(json.dumps(one_task_contract(run_id)))
    initialized = json.loads(run_cli(tmp_path, 'run-init', '--contract', str(contract)).stdout)
    observation = record_source(tmp_path, run_id=run_id)
    link = {
        'target_claim_id': 'financial', 'relationship': 'contextualizes',
        'rationale': 'Interview accounts provide context for the reported cost change, not causal proof.',
        'evidence_observation_ids': [observation],
        'basis': {'entity': 'Example company', 'period': 'different reporting periods',
                  'population': 'interview sample versus whole company', 'measure': 'reported experience versus cost'},
        'alignment': 'different',
    }
    packet = {'run_id': run_id, 'initialized_contract_hash': initialized['contract_hash'], 'task_id': 't1',
              'source_observation_ids': [observation], 'reused_observation_ids': [], 'limitations': ['Synthetic fixture'],
              'claims': [
                  {'claim_id': 'qualitative', 'statement': 'Interviewees describe workflow friction',
                   'claim_kind': 'interpretation', 'evidence_types': ['qualitative'],
                   'evidence_observation_ids': [observation], 'connections': [link]},
                  {'claim_id': 'financial', 'statement': 'The filing reports higher operating costs',
                   'claim_kind': 'factual', 'evidence_types': ['financial', 'quantitative'],
                   'evidence_observation_ids': [observation]},
              ]}
    result = tmp_path / 'result.json'
    result.write_text(json.dumps(packet))
    run_cli(tmp_path, 'run-merge', '--contract', str(contract), '--result', str(result))
    graph = tmp_path / 'mixed.json'
    run_cli(tmp_path, 'graph-export', '--run-id', run_id, '--format', 'json', '--output', str(graph))
    data = json.loads(graph.read_text())
    connections = [e for e in data['entities'] if e['kind'] == 'evidence_connection']
    assert len(connections) == 1
    props = connections[0]['properties']
    assert props['alignment'] == 'different'
    assert props['source_evidence_types'] == ['qualitative']
    assert props['target_evidence_types'] == ['financial', 'quantitative']
    assert props['status'] == 'asserted'
    assert any(e['predicate'] == 'contextualizes' and e['status'] == 'asserted' for e in data['edges'])
    link['target_claim_id'] = 'missing'
    result.write_text(json.dumps(packet))
    rejected = json.loads(run_cli(tmp_path, 'run-merge', '--contract', str(contract), '--result', str(result), expected=2).stdout)
    assert rejected['status'] == 'invalid'
    assert any('target_claim_id' in error for error in rejected['errors'])
