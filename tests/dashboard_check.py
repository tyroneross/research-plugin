#!/usr/bin/env python3
"""Regression checks for the self-contained capability audit dashboard."""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "skills" / "audit-dashboard" / "scripts" / "render_dashboard.py"
EXAMPLE = ROOT / "skills" / "audit-dashboard" / "data" / "example-seven-repo-audit.json"
V2_EXAMPLE = ROOT / "skills" / "audit-dashboard" / "data" / "example-v2-minimal.json"
AREA_IDS = {"overview", "matrix", "subjects", "findings"}


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.area_ids: set[str] = set()
        self.landmarks: set[str] = set()
        self.remote_assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "section" and values.get("id"):
            self.area_ids.add(values["id"] or "")
        if tag in {"header", "nav", "main"}:
            self.landmarks.add(tag)
        attribute = {"link": "href", "script": "src", "img": "src"}.get(tag)
        if attribute:
            target = (values.get(attribute) or "").strip()
            if target.lower().startswith(("http://", "https://", "//")):
                self.remote_assets.append(f"{tag}[{attribute}]={target}")


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RENDERER), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def check_rendered_example(html_text: str, failures: list[str]) -> None:
    payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    score_cells = re.findall(
        r'<td class="score-cell(?: is-best)?"[^>]*>(.*?)</td>',
        html_text,
        flags=re.DOTALL,
    )
    require(len(score_cells) == 49, f"expected 49 score cells, found {len(score_cells)}", failures)
    for index, cell in enumerate(score_cells):
        require(
            re.search(r'class="score-number">[0-3]</span>', cell) is not None,
            f"score cell {index} lacks a numeric score",
            failures,
        )
        require(
            re.search(r'class="score-label">[^<]+</span>', cell) is not None,
            f"score cell {index} lacks a text scale label",
            failures,
        )

    require(
        html_text.count('class="subject-card"') == 7,
        "expected seven subject cards",
        failures,
    )
    matrix = re.search(
        r'<table class="matrix-table">.*?<tbody>(.*?)</tbody>\s*</table>',
        html_text,
        flags=re.DOTALL,
    )
    matrix_rows = re.findall(r"<tr>(.*?)</tr>", matrix.group(1), flags=re.DOTALL) if matrix else []
    require(
        len(matrix_rows) == len(payload["subjects"]),
        f'expected {len(payload["subjects"])} matrix rows, found {len(matrix_rows)}',
        failures,
    )
    for row_index, row in enumerate(matrix_rows):
        row_cells = re.findall(r'<td class="score-cell(?: is-best)?"[^>]*>', row)
        require(
            len(row_cells) == len(payload["dimensions"]),
            f'matrix row {row_index} has {len(row_cells)} score cells, expected {len(payload["dimensions"])}',
            failures,
        )

    for dimension in payload["dimensions"]:
        rendered_label = f'class="dimension-label">{html.escape(dimension["label"], quote=True)}</span>'
        require(
            rendered_label in html_text,
            f'dimension label missing from matrix: {dimension["label"]}',
            failures,
        )
    parser = StructureParser()
    parser.feed(html_text)
    require(parser.area_ids == AREA_IDS, f"area landmarks differ: {parser.area_ids}", failures)
    require(
        {"header", "nav", "main"}.issubset(parser.landmarks),
        f"semantic landmarks missing: {parser.landmarks}",
        failures,
    )
    require(not parser.remote_assets, f"remote asset attributes found: {parser.remote_assets}", failures)
    require(
        re.search(r"@import\b", html_text, re.IGNORECASE) is None,
        "CSS @import found",
        failures,
    )
    require(
        re.search(r"url\(\s*['\"]?(?:https?:)?//", html_text, re.IGNORECASE) is None,
        "remote CSS url() found",
        failures,
    )


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="audit-dashboard-check-") as temp_dir:
        temp = Path(temp_dir)
        rendered = temp / "example.html"
        result = run([str(EXAMPLE), "--out", str(rendered)])
        require(result.returncode == 0, f"example render failed: {result.stderr}", failures)
        if rendered.exists():
            check_rendered_example(rendered.read_text(encoding="utf-8"), failures)
        else:
            failures.append("example render did not create an HTML file")

        v2_rendered = temp / "v2.html"
        require(run([str(V2_EXAMPLE), "--validate-only"]).returncode == 0, "v2 validation failed", failures)
        v2_result = run([str(V2_EXAMPLE), "--out", str(v2_rendered)])
        require(v2_result.returncode == 0, f"v2 render failed: {v2_result.stderr}", failures)
        if v2_rendered.exists():
            v2_text = v2_rendered.read_text(encoding="utf-8")
            score_cells = re.findall(r'<td class="score-cell(?: is-best)?">(.*?)</td>', v2_text, re.DOTALL)
            dialogs = re.findall(r'<dialog class="score-popout" id="score-\d+"', v2_text)
            require('class="stage-header"' in v2_text, "v2 stage group headers missing", failures)
            require(len(score_cells) == 6 and len(dialogs) == 6, "v2 score pop-outs do not match cells", failures)
            require(v2_text.count('class="dot-run"') >= 6, "dot runs do not share one class", failures)
            cite_free = re.sub(r'<[^>]*class="popout-cite"[^>]*>.*?</[^>]+>', '', v2_text, flags=re.DOTALL)
            require(re.search(r'\S+\.(py|ts|tsx|md|json|css|js):\d+', cite_free) is None, "path-like cite outside popout-cite", failures)
            malformed = json.loads(V2_EXAMPLE.read_text(encoding="utf-8"))
            malformed["stages"][0]["dimensionIds"].pop()
            malformed_json = temp / "bad-mece.json"
            malformed_json.write_text(json.dumps(malformed), encoding="utf-8")
            require(run([str(malformed_json), "--validate-only"]).returncode != 0, "missing stage dimension validated", failures)
            malformed = json.loads(V2_EXAMPLE.read_text(encoding="utf-8"))
            malformed["recommendation"]["flow"][0]["approach"] = "other"
            malformed_json.write_text(json.dumps(malformed), encoding="utf-8")
            require(run([str(malformed_json), "--validate-only"]).returncode != 0, "invalid approach validated", failures)

        payload = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        payload["subtitle"] = '<script>alert("payload")</script>'
        injection_json = temp / "injection.json"
        injection_html = temp / "injection.html"
        injection_json.write_text(json.dumps(payload), encoding="utf-8")
        injection_result = run([str(injection_json), "--out", str(injection_html)])
        require(
            injection_result.returncode == 0,
            f"injection fixture render failed: {injection_result.stderr}",
            failures,
        )
        if injection_html.exists():
            injection_text = injection_html.read_text(encoding="utf-8")
            require(
                '<script>alert("payload")</script>' not in injection_text,
                "payload script tag was not escaped",
                failures,
            )
            require(
                "&lt;script&gt;alert(&quot;payload&quot;)&lt;/script&gt;" in injection_text,
                "escaped payload script string not found",
                failures,
            )

        missing = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        del missing["dimensions"]
        missing_json = temp / "missing-dimensions.json"
        missing_json.write_text(json.dumps(missing), encoding="utf-8")
        missing_result = run([str(missing_json), "--validate-only"])
        require(missing_result.returncode != 0, "missing dimensions unexpectedly validated", failures)
        require(
            "$.dimensions" in missing_result.stderr,
            f"missing-dimensions error lacked precise path: {missing_result.stderr}",
            failures,
        )

        extra = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        extra["subjects"][0]["scores"]["D1"]["unsupported"] = "discard me"
        extra_json = temp / "extra-score-field.json"
        extra_json.write_text(json.dumps(extra), encoding="utf-8")
        extra_result = run([str(extra_json), "--validate-only"])
        require(extra_result.returncode != 0, "unsupported score field unexpectedly validated", failures)
        require(
            "$.subjects[0].scores.D1.unsupported" in extra_result.stderr,
            f"extra-field error lacked precise path: {extra_result.stderr}",
            failures,
        )

        control = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        control["\x1b]0;spoofed-title\x07"] = "discard me"
        control_json = temp / "control-key.json"
        control_json.write_text(json.dumps(control), encoding="utf-8")
        control_result = run([str(control_json), "--validate-only"])
        require(control_result.returncode == 2, "control-key error was not controlled", failures)
        require(
            "\x1b" not in control_result.stderr and "\x07" not in control_result.stderr,
            "raw terminal control bytes reached stderr",
            failures,
        )
        require(
            "\\u001b" in control_result.stderr
            and "\\u0007" in control_result.stderr
            and "field is not allowed" in control_result.stderr,
            f"control-key error was not escaped precisely: {control_result.stderr!r}",
            failures,
        )

        surrogate = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        surrogate["title"] = "\ud800"
        surrogate_json = temp / "surrogate.json"
        surrogate_json.write_text(json.dumps(surrogate), encoding="utf-8")
        surrogate_result = run([str(surrogate_json), "--validate-only"])
        require(surrogate_result.returncode == 2, "surrogate error was not controlled", failures)
        require(
            "$.title: contains invalid Unicode" in surrogate_result.stderr,
            f"surrogate error lacked precise path: {surrogate_result.stderr!r}",
            failures,
        )

        invalid_utf8_json = temp / "invalid-utf8.json"
        invalid_utf8_json.write_bytes(b'{"title":"\xff"}')
        invalid_utf8_result = run([str(invalid_utf8_json), "--validate-only"])
        require(invalid_utf8_result.returncode == 2, "invalid UTF-8 error was not controlled", failures)
        require(
            "byte 10: invalid UTF-8 input" in invalid_utf8_result.stderr,
            f"invalid UTF-8 error lacked a byte offset: {invalid_utf8_result.stderr!r}",
            failures,
        )

    if failures:
        print("FAIL dashboard checks:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS dashboard checks: 7 subjects × 7 dimensions, escaping, assets, validation, landmarks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
