#!/usr/bin/env python3
"""Validate a capability audit JSON file and render a self-contained dashboard."""
from __future__ import annotations

import argparse
import html
import json
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, NoReturn
from urllib.parse import quote, urlsplit


HERE = Path(__file__).resolve().parent
THEME = HERE.parent / "assets" / "dashboard-theme.css"
KINDS = {"skill", "plugin", "app", "library", "platform", "surface", "prototype"}
HEALTH_STATES = {"ok", "warn", "bad"}
MARKS = {"verified", "inferred", "unknown"}
SEVERITIES = {"high", "normal", "low"}
FINDING_STATES = {"fixed", "waived", "escalated", "open"}


class ContractError(ValueError):
    """Raised when an audit payload violates the dashboard contract."""


def json_path(parent: str, key: str) -> str:
    """Append a JSON object key without making the diagnostic ambiguous."""
    ascii_identifier = bool(key) and key[0] in "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ascii_identifier = ascii_identifier and all(
        character in "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        for character in key
    )
    if ascii_identifier:
        return f"{parent}.{key}"
    return f"{parent}[{json.dumps(key, ensure_ascii=True)}]"


def console_safe(value: object) -> str:
    """Make terminal diagnostics inert, including control bytes and surrogates."""
    safe: list[str] = []
    for character in str(value):
        codepoint = ord(character)
        category = unicodedata.category(character)
        if category[0] != "C" and category not in {"Zl", "Zp"}:
            safe.append(character)
        elif codepoint <= 0xFF:
            safe.append(f"\\x{codepoint:02x}")
        elif codepoint <= 0xFFFF:
            safe.append(f"\\u{codepoint:04x}")
        else:
            safe.append(f"\\U{codepoint:08x}")
    return "".join(safe)


def fail(path: str, message: str) -> NoReturn:
    raise ContractError(f"{path}: {message}")


def expect_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(path, "expected an object")
    return value


def expect_array(value: Any, path: str, *, minimum: int = 0) -> list[Any]:
    if not isinstance(value, list):
        fail(path, "expected an array")
    if len(value) < minimum:
        fail(path, f"expected at least {minimum} item(s)")
    return value


def expect_string(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        fail(path, "expected a string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        fail(path, "contains invalid Unicode")
    if not allow_empty and not value.strip():
        fail(path, "must not be empty")
    return value


def expect_integer(value: Any, path: str) -> int:
    if type(value) is not int:
        fail(path, "expected an integer")
    return value


def require_fields(
    obj: dict[str, Any], path: str, fields: tuple[str, ...], optional: tuple[str, ...] = ()
) -> None:
    for field in fields:
        if field not in obj:
            fail(json_path(path, field), "required field is missing")
    unexpected = sorted(set(obj) - set(fields) - set(optional))
    if unexpected:
        fail(json_path(path, unexpected[0]), "field is not allowed")


def string_array(value: Any, path: str, *, minimum: int = 0) -> list[str]:
    items = expect_array(value, path, minimum=minimum)
    for index, item in enumerate(items):
        expect_string(item, f"{path}[{index}]")
    return items


def validate_iso(value: Any, path: str) -> str:
    raw = expect_string(value, path)
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        if "T" in normalized or " " in normalized:
            datetime.fromisoformat(normalized)
        else:
            date.fromisoformat(normalized)
    except ValueError:
        fail(path, "expected an ISO 8601 date or date-time")
    return raw


def validate_audit(payload: Any) -> dict[str, Any]:
    root = expect_object(payload, "$")
    require_fields(
        root,
        "$",
        (
            "title",
            "subtitle",
            "generatedAt",
            "source",
            "scale",
            "dimensions",
            "subjects",
            "overlaps",
            "gaps",
            "findings",
            "recommendation",
            "confidence",
        ),
        ("schemaVersion", "stages"),
    )
    if "schemaVersion" in root and root["schemaVersion"] != 2:
        fail("$.schemaVersion", "must be 2 when present")
    expect_string(root["title"], "$.title")
    expect_string(root["subtitle"], "$.subtitle")
    validate_iso(root["generatedAt"], "$.generatedAt")

    source = expect_object(root["source"], "$.source")
    require_fields(source, "$.source", ("label", "path"))
    expect_string(source["label"], "$.source.label")
    expect_string(source["path"], "$.source.path")

    scale = expect_object(root["scale"], "$.scale")
    require_fields(scale, "$.scale", ("min", "max", "labels"))
    minimum = expect_integer(scale["min"], "$.scale.min")
    maximum = expect_integer(scale["max"], "$.scale.max")
    if minimum != 0:
        fail("$.scale.min", "must be 0 so score dots and labels have a stable baseline")
    if maximum != 3:
        fail("$.scale.max", "must be 3 for the capability-audit scale")
    labels = expect_object(scale["labels"], "$.scale.labels")
    expected_labels = {str(score) for score in range(minimum, maximum + 1)}
    unexpected_labels = sorted(set(labels) - expected_labels)
    if unexpected_labels:
        fail(json_path("$.scale.labels", unexpected_labels[0]), "field is not allowed")
    for score in range(minimum, maximum + 1):
        key = str(score)
        if key not in labels:
            fail(f"$.scale.labels.{key}", "required label is missing")
        expect_string(labels[key], f"$.scale.labels.{key}")

    dimensions = expect_array(root["dimensions"], "$.dimensions", minimum=1)
    dimension_ids: list[str] = []
    for index, value in enumerate(dimensions):
        path = f"$.dimensions[{index}]"
        dimension = expect_object(value, path)
        require_fields(dimension, path, ("id", "label", "short", "question"))
        dimension_id = expect_string(dimension["id"], f"{path}.id")
        if dimension_id in dimension_ids:
            fail(f"{path}.id", f"duplicate dimension id {dimension_id!r}")
        dimension_ids.append(dimension_id)
        expect_string(dimension["label"], f"{path}.label")
        expect_string(dimension["short"], f"{path}.short")
        expect_string(dimension["question"], f"{path}.question")

    subjects = expect_array(root["subjects"], "$.subjects", minimum=1)
    subject_ids: list[str] = []
    for index, value in enumerate(subjects):
        path = f"$.subjects[{index}]"
        subject = expect_object(value, path)
        require_fields(
            subject,
            path,
            (
                "id",
                "name",
                "oneLiner",
                "kind",
                "health",
                "scores",
                "strengths",
                "gaps",
                "reuse",
                "role",
            ),
            ("kindNote", "plain", "pipeline"),
        )
        subject_id = expect_string(subject["id"], f"{path}.id")
        if subject_id in subject_ids:
            fail(f"{path}.id", f"duplicate subject id {subject_id!r}")
        subject_ids.append(subject_id)
        expect_string(subject["name"], f"{path}.name")
        expect_string(subject["oneLiner"], f"{path}.oneLiner")
        kind = expect_string(subject["kind"], f"{path}.kind")
        if kind not in KINDS:
            fail(f"{path}.kind", f"expected one of {sorted(KINDS)}")

        health = expect_object(subject["health"], f"{path}.health")
        require_fields(health, f"{path}.health", ("state", "summary", "lastCommit", "tests"))
        state = expect_string(health["state"], f"{path}.health.state")
        if state not in HEALTH_STATES:
            fail(f"{path}.health.state", f"expected one of {sorted(HEALTH_STATES)}")
        for field in ("summary", "lastCommit", "tests"):
            expect_string(health[field], f"{path}.health.{field}")

        scores = expect_object(subject["scores"], f"{path}.scores")
        unexpected = sorted(set(scores) - set(dimension_ids))
        if unexpected:
            fail(
                json_path(f"{path}.scores", unexpected[0]),
                "does not match a declared dimension id",
            )
        for dimension_id in dimension_ids:
            score_path = json_path(f"{path}.scores", dimension_id)
            if dimension_id not in scores:
                fail(score_path, "required dimension score is missing")
            score_entry = expect_object(scores[dimension_id], score_path)
            require_fields(score_entry, score_path, ("score", "evidence", "cite", "mark"), ("plain",))
            score = expect_integer(score_entry["score"], f"{score_path}.score")
            if not minimum <= score <= maximum:
                fail(f"{score_path}.score", f"must be between {minimum} and {maximum}")
            expect_string(score_entry["evidence"], f"{score_path}.evidence")
            expect_string(score_entry["cite"], f"{score_path}.cite")
            mark = expect_string(score_entry["mark"], f"{score_path}.mark")
            if mark not in MARKS:
                fail(f"{score_path}.mark", f"expected one of {sorted(MARKS)}")
            if "plain" in score_entry:
                expect_string(score_entry["plain"], f"{score_path}.plain")

        string_array(subject["strengths"], f"{path}.strengths")
        string_array(subject["gaps"], f"{path}.gaps")
        reuse = expect_array(subject["reuse"], f"{path}.reuse")
        for reuse_index, reuse_value in enumerate(reuse):
            reuse_path = f"{path}.reuse[{reuse_index}]"
            reuse_item = expect_object(reuse_value, reuse_path)
            require_fields(reuse_item, reuse_path, ("path", "what"))
            expect_string(reuse_item["path"], f"{reuse_path}.path")
            expect_string(reuse_item["what"], f"{reuse_path}.what")
        expect_string(subject["role"], f"{path}.role")
        if "kindNote" in subject:
            expect_string(subject["kindNote"], f"{path}.kindNote")
        if "plain" in subject:
            plain = expect_object(subject["plain"], f"{path}.plain")
            require_fields(plain, f"{path}.plain", ("whatItDoes", "howUsed", "unique"))
            for field in ("whatItDoes", "howUsed", "unique"):
                expect_string(plain[field], f"{path}.plain.{field}")
        if "pipeline" in subject:
            pipeline = expect_object(subject["pipeline"], f"{path}.pipeline")
            require_fields(pipeline, f"{path}.pipeline", ("overview", "effectiveness", "flow"))
            expect_string(pipeline["overview"], f"{path}.pipeline.overview")
            effectiveness = expect_object(pipeline["effectiveness"], f"{path}.pipeline.effectiveness")
            require_fields(effectiveness, f"{path}.pipeline.effectiveness", ("score", "why"))
            value = expect_integer(effectiveness["score"], f"{path}.pipeline.effectiveness.score")
            if not minimum <= value <= maximum:
                fail(f"{path}.pipeline.effectiveness.score", f"must be between {minimum} and {maximum}")
            expect_string(effectiveness["why"], f"{path}.pipeline.effectiveness.why")
            flow = expect_array(pipeline["flow"], f"{path}.pipeline.flow")
            for flow_index, flow_item in enumerate(flow):
                flow_path = f"{path}.pipeline.flow[{flow_index}]"
                flow_item = expect_object(flow_item, flow_path)
                require_fields(flow_item, flow_path, ("stage", "how", "effectiveness", "why"))
                expect_string(flow_item["stage"], f"{flow_path}.stage")
                expect_string(flow_item["how"], f"{flow_path}.how")
                value = expect_integer(flow_item["effectiveness"], f"{flow_path}.effectiveness")
                if not minimum <= value <= maximum:
                    fail(f"{flow_path}.effectiveness", f"must be between {minimum} and {maximum}")
                expect_string(flow_item["why"], f"{flow_path}.why")

    valid_subjects = set(subject_ids)
    overlaps = expect_array(root["overlaps"], "$.overlaps")
    for index, value in enumerate(overlaps):
        path = f"$.overlaps[{index}]"
        overlap = expect_object(value, path)
        require_fields(overlap, path, ("capability", "implementations", "keep"))
        expect_string(overlap["capability"], f"{path}.capability")
        implementations = expect_array(overlap["implementations"], f"{path}.implementations", minimum=1)
        for impl_index, impl_value in enumerate(implementations):
            impl_path = f"{path}.implementations[{impl_index}]"
            implementation = expect_object(impl_value, impl_path)
            require_fields(implementation, impl_path, ("subject", "where"))
            subject_ref = expect_string(implementation["subject"], f"{impl_path}.subject")
            if subject_ref not in valid_subjects:
                fail(f"{impl_path}.subject", f"unknown subject id {subject_ref!r}")
            expect_string(implementation["where"], f"{impl_path}.where")
        expect_string(overlap["keep"], f"{path}.keep")

    gaps = expect_array(root["gaps"], "$.gaps")
    for index, value in enumerate(gaps):
        path = f"$.gaps[{index}]"
        gap = expect_object(value, path)
        require_fields(gap, path, ("title", "detail"))
        expect_string(gap["title"], f"{path}.title")
        expect_string(gap["detail"], f"{path}.detail")

    findings = expect_array(root["findings"], "$.findings")
    for index, value in enumerate(findings):
        path = f"$.findings[{index}]"
        finding = expect_object(value, path)
        require_fields(finding, path, ("subject", "severity", "text", "state", "record"))
        subject_ref = expect_string(finding["subject"], f"{path}.subject")
        if subject_ref not in valid_subjects:
            fail(f"{path}.subject", f"unknown subject id {subject_ref!r}")
        severity = expect_string(finding["severity"], f"{path}.severity")
        if severity not in SEVERITIES:
            fail(f"{path}.severity", f"expected one of {sorted(SEVERITIES)}")
        expect_string(finding["text"], f"{path}.text")
        finding_state = expect_string(finding["state"], f"{path}.state")
        if finding_state not in FINDING_STATES:
            fail(f"{path}.state", f"expected one of {sorted(FINDING_STATES)}")
        expect_string(finding["record"], f"{path}.record")

    recommendation = expect_object(root["recommendation"], "$.recommendation")
    require_fields(recommendation, "$.recommendation", ("bottomLine", "spine", "layers", "nextActions"), ("flow", "references"))
    for index, value in enumerate(recommendation.get("references", []) or []):
        path = f"$.recommendation.references[{index}]"
        ref = expect_object(value, path)
        require_fields(ref, path, ("name", "flow", "borrow"), ("url", "sourceTier"))
        for key in ("name", "flow", "borrow"):
            expect_string(ref[key], f"{path}.{key}")
    expect_string(recommendation["bottomLine"], "$.recommendation.bottomLine")
    expect_string(recommendation["spine"], "$.recommendation.spine")
    layers = expect_array(recommendation["layers"], "$.recommendation.layers", minimum=1)
    for index, value in enumerate(layers):
        path = f"$.recommendation.layers[{index}]"
        layer = expect_object(value, path)
        require_fields(layer, path, ("name", "donors", "new"))
        expect_string(layer["name"], f"{path}.name")
        string_array(layer["donors"], f"{path}.donors", minimum=1)
        expect_string(layer["new"], f"{path}.new")
    string_array(recommendation["nextActions"], "$.recommendation.nextActions", minimum=1)

    stages: list[dict[str, Any]] = []
    if "stages" in root:
        raw_stages = expect_array(root["stages"], "$.stages", minimum=1)
        used_dimensions: list[str] = []
        stage_ids: set[str] = set()
        for index, raw_stage in enumerate(raw_stages):
            stage_path = f"$.stages[{index}]"
            stage = expect_object(raw_stage, stage_path)
            require_fields(stage, stage_path, ("id", "label", "dimensionIds", "best", "optimal"))
            stage_id = expect_string(stage["id"], f"{stage_path}.id")
            if stage_id in stage_ids:
                fail(f"{stage_path}.id", "duplicate stage id")
            stage_ids.add(stage_id)
            expect_string(stage["label"], f"{stage_path}.label")
            ids = string_array(stage["dimensionIds"], f"{stage_path}.dimensionIds", minimum=1)
            for dimension_id in ids:
                if dimension_id not in dimension_ids:
                    fail(f"{stage_path}.dimensionIds", f"unknown dimension id {dimension_id!r}")
                used_dimensions.append(dimension_id)
            best_subject = expect_string(stage["best"], f"{stage_path}.best")
            if best_subject not in valid_subjects:
                fail(f"{stage_path}.best", f"unknown subject id {best_subject!r}")
            expect_string(stage["optimal"], f"{stage_path}.optimal")
            stages.append(stage)
        if Counter(used_dimensions) != Counter(dimension_ids):
            fail("$.stages", "dimensionIds must cover every dimension exactly once")
        for subject_index, subject in enumerate(subjects):
            if "pipeline" in subject:
                for flow_index, item in enumerate(subject["pipeline"]["flow"]):
                    if item["stage"] not in stage_ids:
                        fail(f"$.subjects[{subject_index}].pipeline.flow[{flow_index}].stage", "unknown stage id")
        if "flow" in recommendation:
            flow = expect_array(recommendation["flow"], "$.recommendation.flow")
            for index, item in enumerate(flow):
                flow_path = f"$.recommendation.flow[{index}]"
                item = expect_object(item, flow_path)
                require_fields(item, flow_path, ("stage", "title", "approach", "source", "what", "why"))
                if expect_string(item["stage"], f"{flow_path}.stage") not in stage_ids:
                    fail(f"{flow_path}.stage", "unknown stage id")
                for field in ("title", "source", "what", "why"):
                    expect_string(item[field], f"{flow_path}.{field}")
                if expect_string(item["approach"], f"{flow_path}.approach") not in {"existing", "new", "hybrid"}:
                    fail(f"{flow_path}.approach", "expected one of ['existing', 'hybrid', 'new']")

    confidence = expect_object(root["confidence"], "$.confidence")
    require_fields(confidence, "$.confidence", ("context", "verification", "evidence", "overall", "note"))
    for field in ("context", "verification", "evidence", "overall", "note"):
        expect_string(confidence[field], f"$.confidence.{field}")
    return root


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_list(items: list[str], class_name: str = "clean-list") -> str:
    if not items:
        return '<p class="health-summary">None reported.</p>'
    body = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f'<ul class="{class_name}">{body}</ul>'


def score_dots(score: int, maximum: int) -> str:
    return "●" * score + "○" * (maximum - score)


def health_block(health: dict[str, Any]) -> str:
    labels = {"ok": "Healthy", "warn": "Needs review", "bad": "At risk"}
    state = health["state"]
    return (
        f'<span class="pill pill-{esc(state)}">{esc(labels[state])}</span>'
        f'<span class="health-summary">{esc(health["summary"])}</span>'
    )


def render_overview(audit: dict[str, Any], best: dict[str, list[dict[str, Any]]]) -> str:
    findings_by_state = Counter(item["state"] for item in audit["findings"])
    state_order = ("fixed", "waived", "escalated", "open")
    finding_detail = " · ".join(
        f'{findings_by_state.get(state, 0)} {state}' for state in state_order
    )
    best_detail = " · ".join(
        f'{dimension["id"]}: {", ".join(subject["name"] for subject in best[dimension["id"]])}'
        for dimension in audit["dimensions"]
    )
    confidence = audit["confidence"]
    confidence_rows = "".join(
        f"<dt>{esc(label)}</dt><dd>{esc(confidence[key])}</dd>"
        for key, label in (
            ("context", "Context coverage"),
            ("verification", "Verification coverage"),
            ("evidence", "Evidence quality"),
            ("overall", "Overall"),
        )
    )
    next_actions = "".join(
        f"<li>{esc(action)}</li>" for action in audit["recommendation"]["nextActions"]
    )
    composition_layers = "".join(
        f"""<li>
  <h4>{esc(layer["name"])}</h4>
  <p><strong>Donors:</strong> {" · ".join(esc(donor) for donor in layer["donors"])}</p>
  <p><strong>New:</strong> {esc(layer["new"])}</p>
</li>"""
        for layer in audit["recommendation"]["layers"]
    )
    return f"""
<section class="area" id="overview" aria-labelledby="overview-heading">
  <header class="page-header">
    <p class="eyebrow">{esc(audit["source"]["label"])} · {esc(audit["generatedAt"])}</p>
    <h1 id="overview-heading">{esc(audit["title"])}</h1>
    <p class="subtitle">{esc(audit["subtitle"])}</p>
    <p class="authority">Projection of {esc(audit["source"]["label"])}; scores are the auditors&#x27; judgment.</p>
  </header>
  <div class="metric-grid" aria-label="Audit summary metrics">
    <div class="metric"><span class="metric-value">{len(audit["subjects"])}</span><span class="metric-label">Subjects compared</span></div>
    <div class="metric"><span class="metric-value">{len(audit["dimensions"])}</span><span class="metric-label">Dimensions scored</span></div>
    <div class="metric"><span class="metric-value">{len(audit["findings"])}</span><span class="metric-label">Findings by state</span><span class="metric-detail">{esc(finding_detail)}</span></div>
    <div class="metric"><span class="metric-value">{len(best)}</span><span class="metric-label">Column-best dimensions</span><span class="metric-detail">{esc(best_detail)}</span></div>
  </div>
  <article class="panel answer-panel">
    <div class="panel-header"><h2>Bottom line</h2></div>
    <div class="panel-body">
      <p class="bottom-line">{esc(audit["recommendation"]["bottomLine"])}</p>
      <p class="spine"><strong>Recommended spine:</strong> {esc(audit["recommendation"]["spine"])}</p>
    </div>
  </article>
  <article class="panel composition-panel">
    <div class="panel-header"><h3>Composition layers</h3><p>Donor modules and the net-new work recommended for each workflow layer.</p></div>
    <div class="panel-body"><ol class="layer-list">{composition_layers}</ol></div>
  </article>
  <div class="overview-grid">
    <article class="panel">
      <div class="panel-header"><h3>Confidence</h3><p>Coverage and evidence limits from the source audit.</p></div>
      <div class="panel-body"><dl class="confidence-list">{confidence_rows}</dl><p class="health-summary">{esc(confidence["note"])}</p></div>
    </article>
    <article class="panel">
      <div class="panel-header"><h3>Next actions</h3><p>Ordered recommendations from the source audit.</p></div>
      <div class="panel-body"><ol class="next-actions">{next_actions}</ol></div>
    </article>
  </div>
</section>"""


def render_matrix(audit: dict[str, Any], best: dict[str, list[dict[str, Any]]]) -> str:
    scale = audit["scale"]
    maximum = scale["max"]
    headings = "".join(
        f'''<th scope="col" title="{esc(dimension["question"])}">
  <span class="dimension-id">{esc(dimension["id"])}</span>
  <span class="dimension-label">{esc(dimension["label"])}</span>
  <span class="dimension-short">{esc(dimension["short"])}</span>
</th>'''
        for dimension in audit["dimensions"]
    )
    rows: list[str] = []
    for subject in audit["subjects"]:
        cells: list[str] = []
        for dimension in audit["dimensions"]:
            dimension_id = dimension["id"]
            entry = subject["scores"][dimension_id]
            score = entry["score"]
            label = scale["labels"][str(score)]
            is_best = subject in best[dimension_id]
            best_marker = '<span class="best-marker">best</span>' if is_best else ""
            best_context = ", column best" if is_best else ""
            mark_symbol = {"verified": "✅", "inferred": "⚠️", "unknown": "❓"}[entry["mark"]]
            cells.append(
                f"""<td class="score-cell{' is-best' if is_best else ''}" data-score="{score}" data-scale-label="{esc(label)}">
  <details class="score-disclosure">
    <summary aria-label="{esc(subject['name'])}, {esc(dimension['label'])}: {score} of {maximum}, {esc(label)}{best_context}. Evidence details." title="{esc(subject['name'])} · {esc(dimension['label'])} · {score} of {maximum}: {esc(label)}{best_context}">
      <span class="score-summary-content">
        <span class="score-dots" aria-hidden="true">{score_dots(score, maximum)}</span>
        <span class="score-number">{score}</span>{best_marker}
        <span class="score-label">{esc(label)}</span>
      </span>
    </summary>
    <div class="score-evidence">
      <p>{esc(entry["evidence"])}</p>
      <p><strong>Cite:</strong> <code>{esc(entry["cite"])}</code></p>
      <p class="evidence-mark">{mark_symbol} {esc(entry["mark"])}</p>
    </div>
  </details>
</td>"""
            )
        rows.append(
            f"""<tr>
  <th scope="row">{esc(subject["name"])}</th>
  {''.join(cells)}
  <td>{health_block(subject["health"])}</td>
</tr>"""
        )
    return f"""
<section class="area" id="matrix" aria-labelledby="matrix-heading">
  <div class="section-heading">
    <p class="eyebrow">Comparison</p>
    <h2 id="matrix-heading">Capability matrix</h2>
    <p>Open a score to read its evidence, citation, and verification mark. Outlined cells are column bests.</p>
  </div>
  <div class="table-wrap">
    <table class="matrix-table">
      <caption>Subjects by capability dimension on a {scale["min"]}–{scale["max"]} scale; every score includes a numeric value and text label.</caption>
      <thead><tr><th scope="col">Subject</th>{headings}<th scope="col">Health</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</section>"""


def render_subjects(audit: dict[str, Any]) -> str:
    scale = audit["scale"]
    maximum = scale["max"]
    cards: list[str] = []
    for subject in audit["subjects"]:
        mini_parts: list[str] = []
        for dimension in audit["dimensions"]:
            score = subject["scores"][dimension["id"]]["score"]
            label = scale["labels"][str(score)]
            mini_parts.append(
                f"""<div class="mini-score" title="{esc(dimension["question"])}">
  <span class="mini-label"><strong>{esc(dimension["id"])}</strong> {esc(dimension["label"])}</span>
  <span class="score-dots" aria-hidden="true">{score_dots(score, maximum)}</span>
  <span><strong>{score}</strong> <span class="mini-scale-label">{esc(label)}</span></span>
</div>"""
            )
        mini_rows = "".join(mini_parts)
        reuse = "".join(
            f'<li><code>{esc(item["path"])}</code> — {esc(item["what"])}</li>'
            for item in subject["reuse"]
        ) or '<li>None reported.</li>'
        cards.append(
            f"""<article class="subject-card">
  <div class="subject-heading"><h3>{esc(subject["name"])}</h3><span class="kind">{esc(subject["kind"])}</span></div>
  <p class="one-liner">{esc(subject["oneLiner"])}</p>
  <div class="subject-health">{health_block(subject["health"])}<span class="health-summary">Last commit: {esc(subject["health"]["lastCommit"])} · Tests: {esc(subject["health"]["tests"])}</span></div>
  <div class="mini-scores" aria-label="Scores for {esc(subject["name"])}">{mini_rows}</div>
  <div class="subject-columns">
    <div><h4>Strengths</h4>{render_list(subject["strengths"])}</div>
    <div><h4>Gaps</h4>{render_list(subject["gaps"])}</div>
  </div>
  <div class="role-callout"><h4>Reuse candidates</h4><ul class="clean-list reuse-list">{reuse}</ul></div>
  <p class="role-callout"><strong>Role:</strong> {esc(subject["role"])}</p>
</article>"""
        )
    return f"""
<section class="area" id="subjects" aria-labelledby="subjects-heading">
  <div class="section-heading">
    <p class="eyebrow">Evidence by subject</p>
    <h2 id="subjects-heading">Subjects</h2>
    <p>Each card keeps health, scores, strengths, gaps, reuse candidates, and the recommended role together.</p>
  </div>
  <div class="subject-grid">{''.join(cards)}</div>
</section>"""


def render_findings(audit: dict[str, Any]) -> str:
    names = {subject["id"]: subject["name"] for subject in audit["subjects"]}
    overlap_rows = "".join(
        f"""<tr>
  <th scope="row">{esc(overlap["capability"])}</th>
  <td>{'<br>'.join(f'<strong>{esc(names[item["subject"]])}:</strong> {esc(item["where"])}' for item in overlap["implementations"])}</td>
  <td>{esc(overlap["keep"])}</td>
</tr>"""
        for overlap in audit["overlaps"]
    )
    gap_items = "".join(
        f'<li><strong>{esc(gap["title"])}</strong><p>{esc(gap["detail"])}</p></li>'
        for gap in audit["gaps"]
    )
    finding_rows = "".join(
        f"""<tr>
  <th scope="row">{esc(names[finding["subject"]])}</th>
  <td><span class="pill pill-{esc(finding["severity"])}">{esc(finding["severity"])}</span></td>
  <td>{esc(finding["text"])}</td>
  <td><span class="pill pill-{esc(finding["state"])}">{esc(finding["state"])}</span></td>
  <td><code class="record">{esc(finding["record"])}</code></td>
</tr>"""
        for finding in audit["findings"]
    )
    overlaps_panel = f"""<article class="panel">
      <div class="panel-header"><h3>Built more than once</h3><p>The same capability implemented in several places, and which one to keep.</p></div>
      <div class="table-wrap">
        <table><caption>Capability overlap, current implementations, and the implementation to keep.</caption><thead><tr><th scope="col">Capability</th><th scope="col">Implementations</th><th scope="col">Keep</th></tr></thead><tbody>{overlap_rows}</tbody></table>
      </div>
    </article>""" if audit.get("overlaps") else ""
    gaps_panel = f"""<article class="panel">
      <div class="panel-header"><h3>Nobody has this yet</h3><p>Capabilities absent or incomplete across every subject.</p></div>
      <div class="panel-body"><ul class="gap-list">{gap_items}</ul></div>
    </article>""" if audit.get("gaps") else ""
    findings_panel = f"""<article class="panel">
      <div class="panel-header"><h3>Open findings</h3><p>Severity and state are written out, never color-only.</p></div>
      <div class="table-wrap">
        <table><caption>Subject findings with severity, disposition state, and durable record.</caption><thead><tr><th scope="col">Subject</th><th scope="col">Severity</th><th scope="col">Finding</th><th scope="col">State</th><th scope="col">Record</th></tr></thead><tbody>{finding_rows}</tbody></table>
      </div>
    </article>""" if audit.get("findings") else ""
    return f"""
<section class="area" id="findings" aria-labelledby="findings-heading">
  <div class="section-heading">
    <h2 id="findings-heading">Notes</h2>
    <p>What is built more than once, what nobody has yet, and open findings with their record.</p>
  </div>
  <div class="findings-stack">
    {overlaps_panel}
    {gaps_panel}
    {findings_panel}
  </div>
</section>"""


def kind_label(kind: str) -> str:
    return kind.replace("-", " ").title()


def dots(score: int, maximum: int) -> str:
    return f'<span class="dot-run" aria-hidden="true">{score_dots(score, maximum)}</span>'


def popout(dialog_id: str, subject: dict[str, Any], dimension: dict[str, Any], entry: dict[str, Any], scale: dict[str, Any]) -> str:
    score = entry["score"]
    label = scale["labels"][str(score)]
    mark = {"verified": "✅", "inferred": "⚠️", "unknown": "❓"}[entry["mark"]]
    plain = entry.get("plain", entry["evidence"])
    return f'''<dialog class="score-popout" id="{dialog_id}" aria-labelledby="{dialog_id}-title">
  <form method="dialog"><button class="dialog-close" aria-label="Close score details">Close</button></form>
  <h2 id="{dialog_id}-title">{esc(subject["name"])} · {esc(dimension["label"])}</h2>
  <p class="popout-score">{dots(score, scale["max"])} <strong>{score}</strong> {esc(label)}</p>
  <p>{esc(plain)}</p>
  <p class="popout-cite">Where we looked: {esc(entry["cite"])} · {mark} {esc(entry["mark"])}</p>
</dialog>'''


def render_score_cell(subject: dict[str, Any], dimension: dict[str, Any], scale: dict[str, Any], best: dict[str, list[dict[str, Any]]], index: int) -> tuple[str, str]:
    entry = subject["scores"][dimension["id"]]
    score = entry["score"]
    label = scale["labels"][str(score)]
    is_best = subject in best[dimension["id"]]
    dialog_id = f"score-{index}"
    cell = f'''<td class="score-cell{' is-best' if is_best else ''}"><button class="score-trigger" type="button" data-dialog="{dialog_id}" aria-haspopup="dialog" aria-label="{esc(subject['name'])}, {esc(dimension['label'])}: {score} of {scale['max']}, {esc(label)}">
{dots(score, scale["max"])} <span class="score-number">{score}</span>{' <span class="best-marker">Best</span>' if is_best else ''}<span class="score-label">{esc(label)}</span>
</button></td>'''
    return cell, popout(dialog_id, subject, dimension, entry, scale)


def render_recommended_flow(audit: dict[str, Any]) -> str:
    recommendation = audit["recommendation"]
    steps = "".join(f'''<li><h3>{esc(step["title"])}</h3><span class="approach approach-{esc(step["approach"])}">{esc(step["approach"].title())}</span><p>{esc(step["what"])}</p><p class="flow-source"><strong>From:</strong> {esc(step["source"])}</p><p class="muted"><strong>Why:</strong> {esc(step["why"])}</p></li>''' for step in recommendation.get("flow", []))
    references = ""
    if recommendation.get("references"):
        cards = "".join(f'<li><h4>{esc(ref["name"])}</h4><p>{esc(ref["flow"])}</p><p class="borrow"><strong>Borrow:</strong> {esc(ref["borrow"])}</p>{f'<p class="muted"><a href="{esc(ref["url"])}" rel="noopener">Source</a></p>' if ref.get("url") else ""}</li>' for ref in recommendation["references"])
        references = f'<h3 class="sub-heading">Reference pipelines to borrow from</h3><ul class="reference-grid">{cards}</ul>'
    return f'''<section class="area" id="overview" aria-labelledby="overview-heading"><header class="page-header"><p class="eyebrow">{esc(audit["source"]["label"])} · {esc(audit["generatedAt"])} </p><h1>{esc(audit["title"])}</h1><p class="subtitle">{esc(audit["subtitle"])}</p></header><div class="section-heading"><h2 id="overview-heading">Recommended flow</h2><p>{esc(recommendation["bottomLine"])}</p><p class="spine"><strong>Spine:</strong> {esc(recommendation["spine"])}</p></div><ol class="flow-stepper">{steps}</ol>{references}<h3 class="sub-heading">Next actions</h3><ol class="next-actions">{''.join(f'<li>{esc(item)}</li>' for item in recommendation["nextActions"])}</ol></section>'''


def render_pipelines(audit: dict[str, Any]) -> str:
    rows = []
    for index, subject in enumerate(audit["subjects"]):
        pipeline = subject["pipeline"]
        effectiveness = pipeline["effectiveness"]
        flow = "".join(f'<li><strong>{esc(item["stage"])}</strong><p>{esc(item["how"])}</p><p>{dots(item["effectiveness"], audit["scale"]["max"])} {esc(item["why"])}</p></li>' for item in pipeline["flow"])
        rows.append(f'''<article class="pipeline-row"><div><h3>{esc(subject["name"])} <span class="kind">{esc(kind_label(subject["kind"]))}</span></h3><p class="muted">{esc(subject.get("kindNote", ""))}</p></div><p>{esc(pipeline["overview"])}</p><div><p>{dots(effectiveness["score"], audit["scale"]["max"])} <strong>{effectiveness["score"]}</strong> {esc(audit["scale"]["labels"][str(effectiveness["score"])])}</p><p class="muted">{esc(effectiveness["why"])}</p><details><summary>Show flow</summary><ol class="mini-stepper">{flow}</ol></details></div></article>''')
    return f'<section class="area" id="subjects" aria-labelledby="subjects-heading"><div class="section-heading"><h2 id="subjects-heading">Pipelines today</h2><p>Each row shows the current pipeline and its assessed effectiveness.</p></div><div class="pipeline-list">{"".join(rows)}</div></section>'


def render_v2_matrix(audit: dict[str, Any], best: dict[str, list[dict[str, Any]]]) -> tuple[str, str]:
    dimensions = {item["id"]: item for item in audit["dimensions"]}
    stages = audit["stages"]
    headers = "".join(f'<th class="stage-header" scope="colgroup" colspan="{len(stage["dimensionIds"])}">{esc(stage["label"])}</th>' for stage in stages)
    subheaders = "".join(f'<th scope="col"><span class="dimension-label">{esc(dimensions[dimension_id]["short"])}</span></th>' for stage in stages for dimension_id in stage["dimensionIds"])
    dialogs: list[str] = []
    rows: list[str] = []
    index = 0
    for subject in audit["subjects"]:
        cells = []
        for stage in stages:
            for dimension_id in stage["dimensionIds"]:
                cell, dialog = render_score_cell(subject, dimensions[dimension_id], audit["scale"], best, index)
                cells.append(cell); dialogs.append(dialog); index += 1
        plain = subject["plain"]
        rows.append(f'<tr><th scope="row"><strong>{esc(subject["name"])}</strong> <span class="kind">{esc(kind_label(subject["kind"]))}</span><p class="clamp">{esc(plain["whatItDoes"])}</p><button class="more-trigger" data-dialog="subject-{index}">More</button></th>{"".join(cells)}</tr>')
        dialogs.append(f'<dialog class="score-popout" id="subject-{index}"><form method="dialog"><button class="dialog-close">Close</button></form><h2>{esc(subject["name"])}</h2><p>{esc(plain["whatItDoes"])}</p><p>{esc(plain["howUsed"])}</p><p>{esc(plain["unique"])}</p></dialog>')
    names = {subject["id"]: subject["name"] for subject in audit["subjects"]}
    optimal_rows = "".join(f'<tr><th scope="row">{esc(stage["label"])}</th><td>{esc(names.get(stage["best"], stage["best"]))}</td><td>{esc(stage["optimal"])}</td></tr>' for stage in stages)
    optimal = f'<div class="table-wrap optimal-wrap"><table class="optimal-table"><caption>Best subject today and the optimal choice for each stage.</caption><thead><tr><th scope="col">Stage</th><th scope="col">Best today</th><th scope="col">Optimal choice and why</th></tr></thead><tbody>{optimal_rows}</tbody></table></div>'
    ncols = sum(len(stage["dimensionIds"]) for stage in stages)
    colgroup = '<colgroup><col class="col-subject">' + '<col class="col-score">' * ncols + '</colgroup>'
    fallback = ''.join(f'<li>{esc(subject["name"])} · {esc(dimension["label"])}: {esc(subject["scores"][dimension["id"]].get("plain", subject["scores"][dimension["id"]]["evidence"]))}</li>' for subject in audit["subjects"] for dimension in audit["dimensions"])
    section = f'''<section class="area" id="matrix" aria-labelledby="matrix-heading"><div class="section-heading"><h2 id="matrix-heading">Comparison</h2><p>Select a score to read its plain-language reason and evidence location.</p></div><div class="table-wrap"><table class="matrix-table matrix-v2">{colgroup}<caption>Capability comparison grouped by pipeline stage.</caption><thead><tr><th rowspan="2" scope="col">Subject</th>{headers}</tr><tr>{subheaders}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>{optimal}<details class="no-js-fallback"><summary>All score details</summary><ul>{fallback}</ul></details></section>'''
    return section, "".join(dialogs)


def render_v2(audit: dict[str, Any], best: dict[str, list[dict[str, Any]]]) -> str:
    matrix, dialogs = render_v2_matrix(audit, best)
    css = THEME.read_text(encoding="utf-8")
    script = '''<script>let last;document.addEventListener('click',e=>{const b=e.target.closest('[data-dialog]');if(!b)return;last=b;document.getElementById(b.dataset.dialog).showModal()});document.querySelectorAll('dialog').forEach(d=>d.addEventListener('close',()=>last&&last.focus()));document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.matches('.score-trigger,.more-trigger'))e.target.click()});</script>'''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(audit["title"])}</title><style>{css}</style></head><body><a class="skip-link" href="#main-content">Skip to content</a><div class="app-shell"><nav class="sidebar" aria-label="Audit sections"><ul class="nav-list"><li><a class="nav-link" href="#overview">Recommended flow</a></li><li><a class="nav-link" href="#subjects">Pipelines today</a></li><li><a class="nav-link" href="#matrix">Comparison</a></li><li><a class="nav-link" href="#findings">Notes</a></li></ul></nav><main class="workspace" id="main-content">{render_recommended_flow(audit)}{render_pipelines(audit)}{matrix}{render_findings(audit)}</main></div>{dialogs}{script}</body></html>'''


def render_dashboard(audit: dict[str, Any]) -> str:
    css = THEME.read_text(encoding="utf-8")
    best: dict[str, list[dict[str, Any]]] = {}
    for dimension in audit["dimensions"]:
        dimension_id = dimension["id"]
        top_score = max(subject["scores"][dimension_id]["score"] for subject in audit["subjects"])
        best[dimension_id] = [
            subject for subject in audit["subjects"]
            if subject["scores"][dimension_id]["score"] == top_score
        ]
    if "stages" in audit and "pipeline" in audit["subjects"][0] and "flow" in audit["recommendation"]:
        return render_v2(audit, best)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(audit["title"])}</title>
  <style>
{css}
  </style>
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <div class="app-shell">
    <nav class="sidebar" aria-label="Audit sections">
      <p class="product-mark">Capability audit</p>
      <ul class="nav-list">
        <li><a class="nav-link" href="#overview">Overview</a></li>
        <li><a class="nav-link" href="#matrix">Matrix</a></li>
        <li><a class="nav-link" href="#subjects">Subjects</a></li>
        <li><a class="nav-link" href="#findings">Findings</a></li>
      </ul>
      <p class="sidebar-boundary">Static projection · source-led evidence</p>
    </nav>
    <main class="workspace" id="main-content">{render_overview(audit, best)}
{render_matrix(audit, best)}
{render_subjects(audit)}
{render_findings(audit)}
      <footer class="footer">Source: <code>{esc(audit["source"]["path"])}</code> · Generated {esc(audit["generatedAt"])}</footer>
    </main>
  </div>
</body>
</html>
"""


def load_audit(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise ContractError(f"{path}: file not found") from exc
    except UnicodeDecodeError as exc:
        raise ContractError(f"{path}: byte {exc.start}: invalid UTF-8 input") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"{path}:{exc.lineno}:{exc.colno}: invalid JSON: {exc.msg}") from exc
    except OSError as exc:
        raise ContractError(f"{path}: could not read file: {exc}") from exc
    return validate_audit(payload)


def serve_file(path: Path, port: int) -> None:
    content = path.read_bytes()
    dashboard_route = f"/{quote(path.name)}"

    class DashboardHandler(BaseHTTPRequestHandler):
        def respond(self, *, include_body: bool) -> None:
            if urlsplit(self.path).path not in {"/", dashboard_route}:
                self.send_error(404, "Dashboard not found")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if include_body:
                self.wfile.write(content)

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            self.respond(include_body=True)

        def do_HEAD(self) -> None:  # noqa: N802 - stdlib handler API
            self.respond(include_body=False)

    with ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler) as server:
        print(
            f"Serving {console_safe(path.name)} at "
            f"http://127.0.0.1:{port}{console_safe(dashboard_route)}"
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and render a self-contained capability audit dashboard."
    )
    parser.add_argument("audit", type=Path, help="audit JSON file")
    parser.add_argument("--out", type=Path, help="rendered HTML path")
    parser.add_argument("--validate-only", action="store_true", help="validate without rendering")
    parser.add_argument("--serve", action="store_true", help="serve the rendered file on localhost")
    parser.add_argument("--port", type=int, default=8000, help="serve port (default: 8000)")
    args = parser.parse_args(argv)
    if not args.validate_only and args.out is None:
        parser.error("--out is required unless --validate-only is used")
    if args.validate_only and args.serve:
        parser.error("--serve cannot be combined with --validate-only")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        audit = load_audit(args.audit)
        if args.validate_only:
            print(
                f"PASS valid audit: {len(audit['subjects'])} subject(s) × "
                f"{len(audit['dimensions'])} dimension(s)"
            )
            return 0
        output = args.out.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_dashboard(audit), encoding="utf-8")
        print(f"PASS rendered {console_safe(output)}")
        if args.serve:
            serve_file(output, args.port)
        return 0
    except ContractError as exc:
        print(f"ERROR {console_safe(exc)}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR {console_safe(exc)}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
