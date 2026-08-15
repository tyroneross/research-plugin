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
KINDS = {"plugin", "app", "library", "platform"}
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


def require_fields(obj: dict[str, Any], path: str, fields: tuple[str, ...]) -> None:
    for field in fields:
        if field not in obj:
            fail(json_path(path, field), "required field is missing")
    unexpected = sorted(set(obj) - set(fields))
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
    )
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
            require_fields(score_entry, score_path, ("score", "evidence", "cite", "mark"))
            score = expect_integer(score_entry["score"], f"{score_path}.score")
            if not minimum <= score <= maximum:
                fail(f"{score_path}.score", f"must be between {minimum} and {maximum}")
            expect_string(score_entry["evidence"], f"{score_path}.evidence")
            expect_string(score_entry["cite"], f"{score_path}.cite")
            mark = expect_string(score_entry["mark"], f"{score_path}.mark")
            if mark not in MARKS:
                fail(f"{score_path}.mark", f"expected one of {sorted(MARKS)}")

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
    require_fields(recommendation, "$.recommendation", ("bottomLine", "spine", "layers", "nextActions"))
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
    return f"""
<section class="area" id="findings" aria-labelledby="findings-heading">
  <div class="section-heading">
    <p class="eyebrow">Disposition and composition</p>
    <h2 id="findings-heading">Findings</h2>
    <p>Overlaps identify what to consolidate; gaps show what no subject supplies; findings retain severity, state, and record.</p>
  </div>
  <div class="findings-stack">
    <article class="panel">
      <div class="panel-header"><h3>Overlaps</h3><p>The same capability implemented more than once.</p></div>
      <div class="table-wrap">
        <table><caption>Capability overlap, current implementations, and the implementation to keep.</caption><thead><tr><th scope="col">Capability</th><th scope="col">Implementations</th><th scope="col">Keep</th></tr></thead><tbody>{overlap_rows}</tbody></table>
      </div>
    </article>
    <article class="panel">
      <div class="panel-header"><h3>Cross-subject gaps</h3><p>Capabilities absent or incomplete across the audited set.</p></div>
      <div class="panel-body"><ul class="gap-list">{gap_items}</ul></div>
    </article>
    <article class="panel">
      <div class="panel-header"><h3>Findings needing disposition</h3><p>Severity and state are always written, never color-only.</p></div>
      <div class="table-wrap">
        <table><caption>Subject findings with severity, disposition state, and durable record.</caption><thead><tr><th scope="col">Subject</th><th scope="col">Severity</th><th scope="col">Finding</th><th scope="col">State</th><th scope="col">Record</th></tr></thead><tbody>{finding_rows}</tbody></table>
      </div>
    </article>
  </div>
</section>"""


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
