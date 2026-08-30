#!/usr/bin/env python3
"""Static contract checks for the financial-research skill.

Asserts the term-authority, measurement-record, attribution-ladder,
cost-bucket, mechanism, source-priority, guardrail, certainty, and
evidence-package controls exist; that frontmatter parses; and that the
skill stays host-neutral and within the progressive-disclosure line budget.

Deterministic: no network, no LLM, no host tools.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKILL = "skills/financial-research/SKILL.md"
CONTROLS = "skills/financial-research/references/financial-controls.md"
TEMPLATE = "skills/financial-research/references/evidence-package-template.md"
RESEARCH_SKILL = "skills/research/SKILL.md"

HOST_NEUTRAL_FILES = [SKILL, CONTROLS, TEMPLATE]
HOST_SPECIFIC_TOKENS = [
    "WebFetch", "WebSearch", "web__run", "Claude Code", "Claude's", "Codex",
    "in-app Browser", "on-device Browser", "native `Read`", "the Read tool",
    "Grep tool", "Glob tool", "Bash tool",
]
NEUTRAL_WORDING = ["host search tool", "host fetch tool", "host file-read tool"]
MAX_SKILL_LINES = 200

FAILURES: list[str] = []


def read(path: str) -> str:
    full = ROOT / path
    if not full.exists():
        FAILURES.append(f"{path}: file is missing")
        return ""
    return full.read_text(encoding="utf-8")


def require(path: str, *phrases: str) -> None:
    text = read(path)
    if not text:
        return
    missing = [p for p in phrases if p not in text]
    if missing:
        FAILURES.append(f"{path} is missing required content: {missing}")


def require_ci(path: str, *phrases: str) -> None:
    text = read(path).lower()
    if not text:
        return
    missing = [p for p in phrases if p.lower() not in text]
    if missing:
        FAILURES.append(f"{path} is missing required content: {missing}")


def check_frontmatter(path: str, required: dict) -> None:
    text = read(path)
    if not text:
        return
    if not text.startswith("---\n"):
        FAILURES.append(f"{path}: missing YAML frontmatter opening delimiter")
        return
    end = text.find("\n---\n", 3)
    if end == -1:
        FAILURES.append(f"{path}: unterminated YAML frontmatter")
        return
    block = text[4:end]
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        parsed = {}
        for line in block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                parsed[key.strip()] = value.strip().strip('"').strip("'")
    else:
        try:
            parsed = yaml.safe_load(block)
        except Exception as exc:  # pragma: no cover - defensive
            FAILURES.append(f"{path}: frontmatter is not valid YAML: {exc}")
            return
    if not isinstance(parsed, dict):
        FAILURES.append(f"{path}: frontmatter did not parse to a mapping")
        return
    for key, expected in required.items():
        if key not in parsed:
            FAILURES.append(f"{path}: frontmatter missing key {key!r}")
        elif expected is not None and parsed[key] not in (expected, str(expected).lower()):
            FAILURES.append(
                f"{path}: frontmatter {key!r} is {parsed[key]!r}, expected {expected!r}"
            )
    return parsed


def check_trigger_phrases(path: str) -> None:
    text = read(path)
    if not text:
        return
    end = text.find("\n---\n", 3)
    description = text[:end].lower() if end != -1 else ""
    triggers = [
        "margin",
        "cost of sales",
        "cogs",
        "gross margin",
        "operating margin",
        "ebitda",
        "working capital",
        "unit economics",
        "cost bucket",
        "p&l",
        "financial model input",
        "comparable companies",
        "filings",
        "10-k",
        "earnings call",
    ]
    missing = [t for t in triggers if t not in description]
    if missing:
        FAILURES.append(f"{path}: skill description missing trigger phrases: {missing}")


def check_line_budget(path: str) -> None:
    text = read(path)
    if not text:
        return
    lines = len(text.splitlines())
    if lines > MAX_SKILL_LINES:
        FAILURES.append(
            f"{path}: {lines} lines exceeds the {MAX_SKILL_LINES}-line skill budget; "
            f"move detail into references/"
        )


def check_host_neutral(paths: list[str]) -> None:
    for path in paths:
        text = read(path)
        if not text:
            continue
        found = [tok for tok in HOST_SPECIFIC_TOKENS if tok in text]
        if found:
            FAILURES.append(
                f"{path}: host-specific tool or product names must not appear in "
                f"host-neutral content: {found}"
            )
        if not any(w in text for w in NEUTRAL_WORDING):
            FAILURES.append(
                f"{path}: expected host-neutral tool wording, one of {NEUTRAL_WORDING}"
            )


def check_reference_paths(paths: list[str]) -> None:
    """Every markdown path cited in backticks must resolve on disk."""
    import re  # noqa: PLC0415
    pattern = re.compile(
        r"`([./A-Za-z0-9_\-]*(?:references|skills|commands)/[A-Za-z0-9_\-./]+\.md)`"
    )
    for path in paths:
        text = read(path)
        if not text:
            continue
        base = (ROOT / path).parent
        for match in pattern.finditer(text):
            ref = match.group(1)
            if not ((base / ref).exists() or (ROOT / ref).exists()):
                FAILURES.append(f"{path}: cited reference path does not resolve: {ref}")


def check_cli_invocation(path: str) -> None:
    """Where the plugin CLI is invoked, it must resolve all three roots."""
    pattern = '${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py'
    text = read(path)
    if not text:
        return
    for line in text.splitlines():
        if "research.py" in line and line.lstrip().startswith(("python", "python3", "$ python")):
            if pattern not in line:
                FAILURES.append(
                    f"{path}: CLI invocation must use the three-root fallback chain: "
                    f"{line.strip()!r}"
                )


def main() -> int:
    check_frontmatter(SKILL, {"name": "financial-research", "description": None,
                              "user-invocable": False})
    check_trigger_phrases(SKILL)
    check_line_budget(SKILL)

    # Term authority
    require(SKILL, "Term authority", "NPI", "oCOGS", "transformation cost",
            "manufacturing cost", "supply-chain cost")
    require_ci(SKILL, "financial statements")

    # Measurement record fields
    require(SKILL, "Measurement record")
    for field in ["period", "currency", "numerator", "denominator", "scope",
                  "payer", "beneficiary", "P&L location", "reported vs adjusted"]:
        require(SKILL, field)

    # Attribution ladder rungs
    require(SKILL, "Attribution ladder", "Disclosed contribution", "Derived estimate",
            "Directional evidence", "Unsupported hypothesis")
    require_ci(SKILL, "proportional to claim precision")

    # Cost buckets and overlap
    require(SKILL, "Cost buckets and overlap groups")
    require_ci(SKILL, "double counting", "remain unallocated")

    # Mechanism tests
    require(SKILL, "Mechanism tests", "product mix", "pricing", "sourcing",
            "manufacturing automation", "operating leverage",
            "business-model migration")
    require_ci(SKILL, "npi and ramp")

    # Margin layers
    require(SKILL, "Gross margin", "Operating margin", "EBITDA", "Working capital")

    # Source priority + duplicate control
    require(SKILL, "Source priority and duplicate control", "Official filings",
            "expert transcripts", "Analyst research")
    require_ci(SKILL, "auto-reports", "not independent corroboration**")

    # Scope rules / guardrails
    require(SKILL, "Scope rules and guardrails")
    require_ci(SKILL, "never present parent-only", "never combine reported and adjusted")

    # Certainty rubric tied to analyze-plan / analyze-run
    require(SKILL, "Certainty rubric", "**High** —", "**Medium** —", "**Low** —",
            "analyze-plan", "analyze-run")

    # Deliverable shape
    require(SKILL, "Objective", "Controlling evidence", "Source register",
            "Scope rules", "Deliverables", "Known evidence ceilings")

    # References exist and carry their own contract
    require(CONTROLS, "Term authority", "Attribution ladder", "Cost buckets",
            "Mechanism tests", "Reconciliation", "Known evidence ceilings")
    require(TEMPLATE, "## Objective", "## Controlling evidence", "## Source register",
            "## Evidence ledger", "## Claim register", "## Scope rules",
            "## Deliverables", "## Known evidence ceilings",
            "source_id", "evidence_id", "claim_id", "exact_locator")

    check_host_neutral(HOST_NEUTRAL_FILES)
    for path in HOST_NEUTRAL_FILES:
        check_cli_invocation(path)
    check_reference_paths(HOST_NEUTRAL_FILES)

    # Routed from the main research skill's Workflow Detection table
    research_text = read(RESEARCH_SKILL)
    if research_text and "financial-research" not in research_text:
        FAILURES.append(
            f"{RESEARCH_SKILL}: Workflow Detection must route financial questions "
            f"to the financial-research skill"
        )

    if FAILURES:
        print("financial research contract check: FAIL")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("financial research contract check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
