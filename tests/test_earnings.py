"""Earnings pack behavior against synthetic evidence, never the user's corpus."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import research


ROOT = Path(research.__file__).parent


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n")


def init_pack(base):
    args = argparse.Namespace(company="Example Systems", ticker="EXAMPLE", fiscal_year=2026,
                              quarter="Q2", as_of="2026-08-04", period_end="2026-06-30",
                              earnings_date="2026-08-04", source_cutoff="2026-08-04T20:00:00+00:00",
                              base_dir=str(base), json=True)
    assert research.cmd_earnings_init(args) == 0
    return sorted((base / "example-systems" / "fy2026-q2").iterdir())[-1]


def seal(pack):
    """Record a fixture review only after every deterministic check passes."""
    report = research._ep_validate(pack, require_review=False)
    assert report["status"] == "pass", report
    manifest = read_json(pack / "manifest.json")
    manifest["review"] = {"status": "passed", "reviewer": "synthetic-fixture-reviewer",
                          "reviewed_at": research.now_iso(), "input_hash": report["review_input_hash"]}
    write_json(pack / "manifest.json", manifest)
    assert research._ep_validate(pack)["status"] == "pass"


def ledger(pack):
    with (pack / "source-ledger.tsv").open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_ledger(pack, rows):
    with (pack / "source-ledger.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=research.EARNINGS_COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def pack(tmp_path):
    pack = init_pack(tmp_path / "packs")
    manifest = read_json(pack / "manifest.json")
    manifest["latest_period_check"] = {"status": "passed", "checked_at": "2026-08-04T19:00:00+00:00",
                                        "note": "Synthetic fixture event; no real issuer or current-market claim."}
    write_json(pack / "manifest.json", manifest)
    captures = pack / "captures"
    captures.mkdir()
    capture = captures / "example.txt"
    capture.write_text("Synthetic disclosure: revenue 1255000000 USD; gross margin 50 percent; operating margin 20 percent.\n")
    content = read_json(pack / "one-pager-content.json")
    content["headline"]["takeaway"] = "Synthetic results illustrate a validated earnings pack."
    content["sources"] = [{"source_id": "S1", "citation_text": "Synthetic fixture disclosure",
                           "url": "https://example.org/fixture", "path": "", "role": "PRIMARY-DISCLOSURE",
                           "document_type": "release", "tier": "T1", "tier_rationale": "Synthetic original disclosure fixture",
                           "publication_date": "2026-08-04", "accessed_at": "2026-08-04T18:00:00+00:00",
                           "recency_status": "current", "upstream_source_ids": [], "capture_path": "captures/example.txt",
                           "content_hash": "sha256:" + hashlib.sha256(capture.read_bytes()).hexdigest(), "observation_id": "obs-example"}]
    rows = []
    for cid, label, value, unit, display, shown in [
        ("C1", "Revenue", "1255000000", "USD", {"scale": "1000000000", "decimals": 2, "prefix": "$", "suffix": "B"}, "$1.26B"),
        ("C2", "Gross margin", "50", "percent", {"scale": "1", "decimals": 1, "prefix": "", "suffix": "%"}, "50.0%"),
        ("C3", "Operating margin", "20", "percent", {"scale": "1", "decimals": 1, "prefix": "", "suffix": "%"}, "20.0%"),
    ]:
        rows.append({**dict.fromkeys(research.EARNINGS_COLUMNS, ""), "claim_id": cid, "kind": "metric",
                     "statement": f"Synthetic {label.lower()} is {value} {unit}.", "value": value, "unit": unit,
                     "period": "FY2026 Q2", "scope": "consolidated", "basis": "GAAP", "status": "reported",
                     "material": "true", "evidence_class": "reported_fact", "source_ids": '["S1"]',
                     "locators": '{"S1":"line 1"}', "validation": "source_only", "formula": "",
                     "denominator": "revenue" if unit == "percent" else "not_applicable: absolute revenue",
                     "grain": "company-quarter", "receipt": "", "depends_on": "[]"})
        content["financial_highlights"].append({"claim_id": cid, "label": label, "display_value": shown,
                                               "display": display, "comparison": "Not sourced", "insight": "Synthetic illustration.",
                                               "unit": unit, "period": "FY2026 Q2", "scope": "consolidated", "basis": "GAAP",
                                               "status": "reported", "source_ids": ["S1"], "footnote_ids": []})
    rows.append({**dict.fromkeys(research.EARNINGS_COLUMNS, ""), "claim_id": "C4", "kind": "inference",
                 "statement": "Synthetic revenue could support future investment.", "status": "estimated",
                 "material": "true", "evidence_class": "inference", "source_ids": '["S1"]',
                 "locators": '{"S1":"line 1"}', "validation": "source_only", "depends_on": '["C1"]'})
    content["financial_drivers"] = [{"text": rows[-1]["statement"], "claim_ids": ["C4"], "evidence_class": "inference",
                                      "confidence": "low", "source_ids": ["S1"], "mechanism": "Illustrative reinvestment capacity",
                                      "time_horizon": "next fiscal year", "monitor": "Disclosed investment",
                                      "disconfirming_evidence": "Investment falls despite unchanged revenue"}]
    write_json(pack / "one-pager-content.json", content)
    write_ledger(pack, rows)
    (pack / "webex-brief.md").write_text(f"**{content['headline']['title']}**\n\n**Synthetic results support an illustrative thesis.**\n   •\tRevenue was $1.26B in this synthetic fixture.\n")
    (pack / "one-pager-content.md").write_text("# Synthetic earnings content\n\nIllustrative evidence-backed handoff; no real company claims.\n")
    seal(pack)
    return pack


def cli(tmp_path, script, *args):
    env = {**os.environ, "RESEARCH_CONTENT_DIR": str(tmp_path / "corpus"), "RESEARCH_INDEX_DIR": str(tmp_path / "index")}
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                          cwd=tmp_path, env=env, text=True, capture_output=True)


def revise(pack, scope, capsys, *claim_ids):
    args = argparse.Namespace(path=str(pack), scope=scope, change_note="Synthetic revision", claim_id=list(claim_ids), as_of=None, json=True)
    capsys.readouterr()
    assert research.cmd_earnings_revise(args) == 0
    report = json.loads(capsys.readouterr().out)
    return Path(report["path"]), report


def test_helpers_work_from_another_directory_and_scaffold_is_not_complete(tmp_path):
    result = cli(tmp_path, "init_earnings_output.py", "--company", "Example", "--ticker", "EX", "--fiscal-year", "2026", "--quarter", "Q2", "--as-of", "2026-08-04", "--json")
    assert result.returncode == 0, result.stderr
    pack = Path(json.loads(result.stdout)["path"])
    assert pack.is_relative_to(tmp_path / "corpus" / "earnings")
    assert not (tmp_path / "index").exists()
    scaffold = cli(tmp_path, "validate_earnings_output.py", pack, "--scaffold", "--json")
    assert scaffold.returncode == 0 and json.loads(scaffold.stdout)["status"] == "scaffold"
    complete = cli(tmp_path, "validate_earnings_output.py", pack, "--json")
    assert complete.returncode == 2 and json.loads(complete.stdout)["status"] == "fail"


def test_complete_pack_validation_is_read_only(pack, tmp_path):
    before = {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}
    result = cli(tmp_path, "validate_earnings_output.py", pack, "--json")
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["status"] == "pass"
    assert before == {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}
    assert not (tmp_path / "index").exists()


def test_committed_synthetic_example_passes_complete_validation():
    example = ROOT / "tests/fixtures/earnings-v1/2026-08-04-v1"
    report = research._ep_validate(example)
    assert report["status"] == "pass", report


def test_concurrent_version_allocation_never_overwrites(tmp_path):
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        allocated = list(pool.map(lambda _: research._ep_allocate(tmp_path, "2026-08-04"), range(16)))
    assert sorted(version for _, version in allocated) == list(range(1, 17))
    assert len({path for path, _ in allocated}) == 16


@pytest.mark.parametrize("change,match", [
    ({"fiscal_year": True}, "fiscal_year"),
    ({"schema_version": "1.1"}, "unsupported earnings schema"),
    ({"version": 2}, "directory name"),
    ({"source_cutoff": "2026-08-04T20:00:00"}, "timezone"),
    ({"unexpected": True}, "unknown fields"),
    ({"source_state": "call_included"}, "transcript"),
])
def test_manifest_rejects_invalid_types_and_event_basis(pack, change, match):
    manifest = read_json(pack / "manifest.json")
    manifest.update(change)
    write_json(pack / "manifest.json", manifest)
    assert match in " ".join(research._ep_validate(pack)["errors"])


@pytest.mark.parametrize("field,value,match", [
    ("value", "NaN", "finite"), ("value", "Infinity", "finite"),
    ("material", "yes", "material"), ("validation", "failed", "material claim"),
    ("source_ids", '["missing"]', "unknown source"),
    ("locators", '{}', "locator"), ("depends_on", '["C4"]', "cycle"),
])
def test_ledger_rejects_unusable_claims(pack, field, value, match):
    rows = ledger(pack)
    rows[0][field] = value
    write_ledger(pack, rows)
    assert match in " ".join(research._ep_validate(pack)["errors"])


def test_duplicate_claims_are_rejected(pack):
    rows = ledger(pack)
    write_ledger(pack, rows + [rows[0]])
    assert "duplicate claim_id" in " ".join(research._ep_validate(pack)["errors"])


@pytest.mark.parametrize("field,value,match", [
    ("display_value", "$1.25B", "displayed value"),
    ("basis", "non-GAAP", "basis mismatch"),
    ("unit", "EUR", "unit mismatch"),
    ("period", "FY2026 Q1", "period mismatch"),
    ("claim_id", "unknown", "claim ID"),
    ("footnote_ids", ["unknown"], "footnote"),
])
def test_highlights_are_bound_to_ledger(pack, field, value, match):
    content = read_json(pack / "one-pager-content.json")
    content["financial_highlights"][0][field] = value
    write_json(pack / "one-pager-content.json", content)
    assert match in " ".join(research._ep_validate(pack)["errors"])


def test_capture_changes_and_pending_reviews_block_complete_status(pack):
    (pack / "captures/example.txt").write_text("Changed synthetic evidence")
    assert "capture hash" in " ".join(research._ep_validate(pack)["errors"])


def test_edited_prose_invalidates_pack_review(pack):
    with (pack / "webex-brief.md").open("a") as handle:
        handle.write("\nA materially changed interpretation.\n")
    report = research._ep_validate(pack)
    assert "stale" in " ".join(report["errors"])
    assert report["review_input_hash"]


def test_inference_requires_a_disconfirming_test(pack):
    content = read_json(pack / "one-pager-content.json")
    del content["financial_drivers"][0]["disconfirming_evidence"]
    write_json(pack / "one-pager-content.json", content)
    assert "disconfirming" in " ".join(research._ep_validate(pack)["errors"])


@pytest.mark.parametrize("bad_path", ["../outside.txt", "/etc/hosts"])
def test_capture_paths_cannot_escape_pack(pack, bad_path):
    content = read_json(pack / "one-pager-content.json")
    content["sources"][0]["capture_path"] = bad_path
    write_json(pack / "one-pager-content.json", content)
    assert "inside pack" in " ".join(research._ep_validate(pack)["errors"])


def test_symlink_and_fifo_artifacts_are_rejected_without_opening(pack):
    path = pack / "captures/example.txt"
    data = path.read_bytes()
    path.unlink()
    outside = pack.parent / "outside.txt"
    outside.write_bytes(data)
    path.symlink_to(outside)
    assert "symlink" in " ".join(research._ep_validate(pack)["errors"])
    path.unlink()
    os.mkfifo(path)
    assert "regular file" in " ".join(research._ep_validate(pack)["errors"])


def test_duplicate_json_keys_fail_cleanly(pack):
    path = pack / "manifest.json"
    path.write_text('{"schema_version":"research.earnings.v1","schema_version":"other"}')
    assert "duplicate JSON key" in " ".join(research._ep_validate(pack)["errors"])


def test_format_revision_preserves_evidence_and_requires_new_review(pack, capsys):
    original = {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}
    new, report = revise(pack, "formatting", capsys)
    assert report["invalidated_claim_ids"] == []
    assert new != pack
    assert (new / "source-ledger.tsv").read_bytes() == original[Path("source-ledger.tsv")]
    assert "pending" in " ".join(research._ep_validate(new)["errors"])
    content = read_json(new / "one-pager-content.json")
    content["financial_highlights"][0]["display"]["decimals"] = 1
    content["financial_highlights"][0]["display_value"] = "$1.3B"
    write_json(new / "one-pager-content.json", content)
    seal(new)
    assert original == {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}


def test_format_revision_preserves_existing_crlf_ledger_bytes(pack, capsys):
    path = pack / "source-ledger.tsv"
    original = path.read_bytes().replace(b"\n", b"\r\n")
    path.write_bytes(original)
    seal(pack)
    new, _ = revise(pack, "formatting", capsys)
    assert (new / "source-ledger.tsv").read_bytes() == original
    assert research._ep_validate(new, require_review=False)["status"] == "pass"


def test_wording_revision_cannot_change_claim_meaning(pack, capsys):
    new, _ = revise(pack, "wording", capsys)
    rows = ledger(new)
    rows[0]["statement"] = "Different substantive claim"
    write_ledger(new, rows)
    assert "protected" in " ".join(research._ep_validate(new)["errors"])


def test_financial_revision_invalidates_transitive_dependencies(pack, capsys):
    new, report = revise(pack, "financial-data", capsys, "C1")
    assert report["invalidated_claim_ids"] == ["C1", "C4"]
    states = {row["claim_id"]: row["validation"] for row in ledger(new)}
    assert states == {"C1": "pending", "C2": "source_only", "C3": "source_only", "C4": "pending"}
    assert "pending" in " ".join(research._ep_validate(new)["errors"])


def test_interpretation_revision_preserves_numeric_verification(pack, capsys):
    new, report = revise(pack, "interpretation", capsys, "C4")
    assert report["invalidated_claim_ids"] == ["C4"]
    assert ledger(new)[0]["validation"] == "source_only"


def test_source_refresh_requires_new_event_check(pack, capsys):
    new, report = revise(pack, "source-refresh", capsys)
    assert report["invalidated_claim_ids"] == ["C1", "C2", "C3", "C4"]
    assert read_json(new / "manifest.json")["latest_period_check"]["status"] == "pending"


def test_financial_revision_can_complete_after_research_and_review(pack, capsys):
    new, _ = revise(pack, "financial-data", capsys, "C1")
    capture = new / "captures/example.txt"
    capture.write_text("Synthetic corrected disclosure: revenue 1300000000 USD; gross margin 50 percent; operating margin 20 percent.\n")
    content = read_json(new / "one-pager-content.json")
    content["sources"][0]["content_hash"] = "sha256:" + hashlib.sha256(capture.read_bytes()).hexdigest()
    content["sources"][0]["observation_id"] = "obs-corrected"
    content["financial_highlights"][0]["display_value"] = "$1.30B"
    write_json(new / "one-pager-content.json", content)
    rows = ledger(new)
    rows[0].update(value="1300000000", statement="Synthetic corrected revenue is 1300000000 USD.")
    for row in rows:
        if row["validation"] == "pending":
            row["validation"] = "source_only"
    write_ledger(new, rows)
    # A host reviews the changed disclosure and prose before attesting.
    (new / "webex-brief.md").write_text("**Example Systems FY2026 Q2 Earnings Update**\n\n**The synthetic correction changes revenue.**\n   •\tCorrected synthetic revenue is $1.30B.\n")
    seal(new)
    assert research._ep_validate(pack)["status"] == "pass"


def test_failed_nonmaterial_dependency_cannot_support_a_published_claim(pack):
    rows = ledger(pack)
    rows[0].update(material="false", validation="failed")
    write_ledger(pack, rows)
    assert "depends on an unvalidated claim" in " ".join(research._ep_validate(pack)["errors"])


@pytest.mark.parametrize("value", [[], None, "not an object"])
def test_malformed_content_returns_json_failure_without_traceback(pack, tmp_path, value):
    write_json(pack / "one-pager-content.json", value)
    result = cli(tmp_path, "validate_earnings_output.py", pack, "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "fail"
    assert "Traceback" not in result.stderr


def test_revision_rejects_an_unreviewed_parent(pack, tmp_path):
    manifest = read_json(pack / "manifest.json")
    manifest["review"]["status"] = "pending"
    write_json(pack / "manifest.json", manifest)
    before = set(pack.parent.iterdir())
    result = cli(tmp_path, "revise_earnings_output.py", pack, "--scope", "wording", "--change-note", "Edit wording", "--json")
    assert result.returncode == 2
    assert set(pack.parent.iterdir()) == before


def test_format_revision_cannot_change_source_review_basis(pack, capsys):
    new, _ = revise(pack, "formatting", capsys)
    content = read_json(new / "one-pager-content.json")
    content["sources"][0]["tier_rationale"] = "Different assessment of source authority"
    write_json(new / "one-pager-content.json", content)
    assert "protected" in " ".join(research._ep_validate(new)["errors"])


def test_review_cannot_precede_pack_creation(pack):
    manifest = read_json(pack / "manifest.json")
    manifest["review"]["reviewed_at"] = "2026-08-04T20:00:00+00:00"
    write_json(pack / "manifest.json", manifest)
    assert "between pack creation and now" in " ".join(research._ep_validate(pack)["errors"])


def test_displayed_nonmaterial_claim_still_requires_eligible_sources(pack):
    rows = ledger(pack)
    for row in rows:
        row["material"] = "false"
    write_ledger(pack, rows)
    content = read_json(pack / "one-pager-content.json")
    content["sources"][0]["role"] = "AI-DISCOVERY"
    write_json(pack / "one-pager-content.json", content)
    assert "published claim" in " ".join(research._ep_validate(pack)["errors"])


def test_revision_write_failure_preserves_parent_and_removes_only_new_copy(pack, capsys, monkeypatch):
    before = {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}
    monkeypatch.setattr(research, "_ep_write_ledger", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    args = argparse.Namespace(path=str(pack), scope="financial-data", change_note="Correct revenue", claim_id=["C1"], as_of=None, json=True)
    assert research.cmd_earnings_revise(args) == 2
    assert list(pack.parent.iterdir()) == [pack]
    assert before == {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}


@pytest.mark.parametrize("value,expected", [("1.255", "1.26"), ("-1.255", "-1.26"), ("0", "0.00")])
def test_display_uses_declared_decimal_rounding(value, expected):
    assert research._ep_display(value, {"scale": "1", "decimals": 2, "prefix": "", "suffix": ""}) == expected


def test_revision_cli_rejects_missing_claim_without_creating_directory(pack, tmp_path):
    before = set(pack.parent.iterdir())
    result = cli(tmp_path, "revise_earnings_output.py", pack, "--scope", "financial-data", "--change-note", "Change revenue", "--json")
    assert result.returncode == 2
    assert "--claim-id" in json.loads(result.stdout)["errors"][0]
    assert set(pack.parent.iterdir()) == before


def test_failed_write_cleans_only_its_new_pack(tmp_path, monkeypatch):
    base = tmp_path / "packs"
    parent = init_pack(base)
    monkeypatch.setattr(research, "_ep_write_json", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    args = argparse.Namespace(company="Example Systems", ticker="EXAMPLE", fiscal_year=2026, quarter="Q2", as_of="2026-08-04",
                              period_end=None, earnings_date=None, source_cutoff=None, base_dir=str(base), json=True)
    assert research.cmd_earnings_init(args) == 2
    assert list(parent.parent.iterdir()) == [parent]


def test_actual_calculator_receipt_is_reused_and_recomputed(pack, tmp_path):
    env = {**os.environ, "RESEARCH_CONTENT_DIR": str(tmp_path / "calc-corpus"), "RESEARCH_INDEX_DIR": str(tmp_path / "calc-index")}
    capture = pack / "captures/example.txt"
    manifest = tmp_path / "source.json"
    manifest.write_text(json.dumps({"url": "https://example.org/fixture", "name": "Synthetic disclosure",
                                     "content_hash": "sha256:" + hashlib.sha256(capture.read_bytes()).hexdigest(),
                                     "parser": "fixture", "raw_ref": str(capture), "captured": "2026-08-04T18:00:00+00:00",
                                     "published_at": "2026-08-04", "locator": "line 1"}))
    observed = subprocess.run([sys.executable, str(ROOT / "research.py"), "source-record", "--manifest", str(manifest), "--run-id", "earnings-test"], env=env, text=True, capture_output=True)
    assert observed.returncode == 0, observed.stderr
    observation_id = json.loads(observed.stdout)["observation_id"]
    spec = tmp_path / "calculation.json"
    spec.write_text(json.dumps({"run_id": "earnings-test", "claim_id": "C1", "formula": "revenue / 2",
                               "unit": "USD", "denominator": "not_applicable: absolute revenue", "grain": "company-quarter",
                               "inputs": [{"name": "revenue", "value": "2510000000", "source_observation_id": observation_id}],
                               "assumptions": ["Synthetic fixture calculation"], "checks": [{"name": "positive", "expression": "result > 0"}]}))
    calculated = subprocess.run([sys.executable, str(ROOT / "research.py"), "calculate", "--spec", str(spec)], env=env, text=True, capture_output=True)
    assert calculated.returncode == 0, calculated.stderr
    receipt = read_json(Path(calculated.stdout.splitlines()[0]))
    (pack / "calculations").mkdir()
    write_json(pack / "calculations/C1.json", receipt)
    content = read_json(pack / "one-pager-content.json")
    content["sources"][0]["observation_id"] = observation_id
    content["financial_highlights"][0]["status"] = "derived"
    write_json(pack / "one-pager-content.json", content)
    rows = ledger(pack)
    rows[0].update(status="derived", validation="passed", formula="revenue / 2", receipt="calculations/C1.json")
    write_ledger(pack, rows)
    seal(pack)
    receipt["result_text"] = "1"
    # A rewritten hash alone cannot make incorrect arithmetic pass.
    receipt["receipt_hash"] = "sha256:" + research._sha256_text(research._canonical_json({k: v for k, v in receipt.items() if k != "receipt_hash"}))
    write_json(pack / "calculations/C1.json", receipt)
    assert "calculation result mismatch" in " ".join(research._ep_validate(pack)["errors"])
