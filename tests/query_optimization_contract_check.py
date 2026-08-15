#!/usr/bin/env python3
"""Static contract checks for query optimization and deep-research orchestration.

Covers the two host-neutral references added in v0.6.0
(`query-optimization.md`, `deep-orchestration.md`), the `/research:optimize`
command surface, and the Phase 1 framing contract in the research SKILL.

Deterministic: no network, no LLM, no host tools.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUERY_OPT = "skills/research/references/query-optimization.md"
DEEP_ORCH = "skills/research/references/deep-orchestration.md"
OPTIMIZE_CMD = "commands/optimize.md"
SKILL = "skills/research/SKILL.md"

# Files that must never name a single host's proprietary tool.
HOST_NEUTRAL_FILES = [QUERY_OPT, DEEP_ORCH, OPTIMIZE_CMD]
# Host-specific tool and product names that must not appear in host-neutral content.
HOST_SPECIFIC_TOKENS = [
    "WebFetch", "WebSearch", "web__run", "Claude Code", "Claude's", "Codex",
    "in-app Browser", "on-device Browser", "native `Read`", "the Read tool",
    "Grep tool", "Glob tool", "Bash tool",
]
# Neutral wording that must accompany any tool reference.
NEUTRAL_WORDING = ["host search tool", "host fetch tool", "host file-read tool"]

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
    """Case-insensitive variant for prose phrases."""
    text = read(path).lower()
    if not text:
        return
    missing = [p for p in phrases if p.lower() not in text]
    if missing:
        FAILURES.append(f"{path} is missing required content: {missing}")


def check_frontmatter(path: str, *required_keys: str) -> None:
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
    keys = {}
    for line in block.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if ":" not in line:
            FAILURES.append(f"{path}: frontmatter line is not a key/value pair: {line!r}")
            continue
        key, value = line.split(":", 1)
        keys[key.strip()] = value.strip()
    for key in required_keys:
        if key not in keys:
            FAILURES.append(f"{path}: frontmatter missing key {key!r}")
    # A value starting with an unquoted YAML indicator breaks strict parsers.
    for key, value in keys.items():
        if value[:1] in {"[", "{", "*", "&", "!", "|", ">", "%", "@", "`"}:
            FAILURES.append(
                f"{path}: frontmatter value for {key!r} starts with an unquoted "
                f"YAML indicator: {value[:1]!r}"
            )
    try:
        import yaml  # noqa: PLC0415
    except ImportError:
        return
    try:
        parsed = yaml.safe_load(block)
    except Exception as exc:  # pragma: no cover - defensive
        FAILURES.append(f"{path}: frontmatter is not valid YAML: {exc}")
        return
    if not isinstance(parsed, dict):
        FAILURES.append(f"{path}: frontmatter did not parse to a mapping")


def check_section_contract_columns(path: str) -> None:
    """The section-contract table must be a real markdown table with the five
    columns, in order, followed by a delimiter row."""
    text = read(path)
    if not text:
        return
    columns = [
        "Section",
        "Exact question",
        "Evidence required",
        "Expected output",
        "Completion rule",
    ]
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells != columns:
            continue
        # Header must be followed by a markdown delimiter row.
        if i + 1 < len(lines) and re.fullmatch(r"\|[-:\s|]+\|", lines[i + 1].strip()):
            return
        FAILURES.append(
            f"{path}: section-contract header at line {i + 1} is not followed by a "
            f"markdown delimiter row"
        )
        return
    FAILURES.append(
        f"{path}: no section-contract table with the exact ordered columns {columns} "
        f"(must be a real markdown table, not prose)"
    )


def check_readiness_dimensions(path: str) -> None:
    """Readiness score is 8 dimensions x 0-3 = 0-24."""
    text = read(path)
    if not text:
        return
    dimensions = [
        "Decision",
        "Scope",
        "Time / period",
        "Definitions",
        "Evidence expectations",
        "Metrics / basis",
        "Comparisons",
        "Output requirements",
    ]
    missing = [d for d in dimensions if f"**{d}**" not in text]
    if missing:
        FAILURES.append(f"{path}: readiness table missing dimensions: {missing}")
    for band in ["≥ 18", "12–17", "< 12"]:
        if band not in text:
            FAILURES.append(f"{path}: readiness threshold band {band!r} not documented")


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
    pattern = re.compile(r"`([./A-Za-z0-9_\-]*(?:references|skills|commands)/[A-Za-z0-9_\-./]+\.md)`")
    for path in paths:
        text = read(path)
        if not text:
            continue
        base = (ROOT / path).parent
        for match in pattern.finditer(text):
            ref = match.group(1)
            if not ((base / ref).exists() or (ROOT / ref).exists()):
                FAILURES.append(f"{path}: cited reference path does not resolve: {ref}")


def check_cli_invocation(paths: list[str]) -> None:
    pattern = '${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py'
    for path in paths:
        text = read(path)
        if text and pattern not in text:
            FAILURES.append(f"{path}: CLI invocation must use the three-root fallback chain")


# Phrasings that instruct the agent to collapse a request into a single question.
COLLAPSE_PATTERNS = [
    r"one clear question",
    r"a single (?:well-formed |specific |clear )?question",
    r"(?:reduce|rewrite|restate|condense|collapse|merge|combine)[^.\n]{0,80}"
    r"(?:into|as|to) (?:one|a single)[^.\n]{0,30}question",
    r"(?:one|a single) question(?: only)?\b[^.\n]{0,40}(?:always|must|should)",
]

# Invariants the Phase 1 block itself must state.
PHASE_ONE_INVARIANTS = [
    "never force distinct questions into one",
    "meta-question",
    "mece",
    "section heading",
    "decision card",
    "section contract",
]


def check_phase_one_block(path: str) -> None:
    """Assert against the Phase 1 section only, so tokens elsewhere in the file
    cannot satisfy the requirement after Phase 1 is gutted."""
    text = read(path)
    if not text:
        return
    start = text.find("### Phase 1")
    if start == -1:
        FAILURES.append(f"{path}: no '### Phase 1' section found")
        return
    end = text.find("### Phase 2", start)
    block = text[start:end if end != -1 else len(text)]
    lowered = block.lower()

    for pattern in COLLAPSE_PATTERNS:
        match = re.search(pattern, lowered)
        if match and "never force distinct questions into one" not in match.group(0):
            FAILURES.append(
                f"{path}: Phase 1 instructs collapsing the request into one question: "
                f"{match.group(0)!r}"
            )

    missing = [inv for inv in PHASE_ONE_INVARIANTS if inv not in lowered]
    if missing:
        FAILURES.append(f"{path}: Phase 1 block is missing invariants: {missing}")

    # The five evidence checks must be demoted to inside-theme checks, not headings.
    if not re.search(r"[*_]*(inside|within)[*_]* each theme", lowered):
        FAILURES.append(
            f"{path}: Phase 1 must state that scope/direct answer/drivers/boundaries/"
            f"confidence are evidence checks inside each theme, not section headings"
        )


def main() -> int:
    # Query optimization contract
    require(
        QUERY_OPT,
        "USER-PROVIDED FACTS",
        "WORKING HYPOTHESES",
        "REQUESTED TESTS",
        "UNSUPPORTED ASSUMPTIONS",
        "Decision this research will inform:",
        "meta-question",
        "MECE",
        "Q0",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Readiness score (0–24)",
    )
    require_ci(
        QUERY_OPT,
        "never force distinct questions into one",
        "evidence checks",
        "one ask",
        "basis-defined",
        "neutral first",
    )
    check_section_contract_columns(QUERY_OPT)
    check_readiness_dimensions(QUERY_OPT)
    # The worked example must carry more than one meta-question.
    qo_text = read(QUERY_OPT)
    if qo_text and not ("MQ1" in qo_text and "MQ2" in qo_text):
        FAILURES.append(f"{QUERY_OPT}: worked example must show at least two meta-questions")

    # Deep-research orchestration contract
    require(
        DEEP_ORCH,
        "Query ledger",
        "Source register",
        "Claim register",
        "## Reconcile",
        "Cross-section synthesis",
        "source_id",
        "claim_id",
        "corroboration class",
        "exact_locator",
        "unresolved gaps",
    )
    require_ci(
        DEEP_ORCH,
        "one owner per concept",
        "light",
        "standard",
        "deep",
        "quick",
        "balanced",
    )
    check_section_contract_columns(DEEP_ORCH)

    # Command surface
    check_frontmatter(OPTIMIZE_CMD, "description", "argument-hint", "allowed-tools")
    require(
        OPTIMIZE_CMD,
        "query-optimization.md",
        "Never merge distinct questions",
        "Completion rule",
        "Readiness score",
    )

    # Host neutrality + CLI invocation shape
    check_host_neutral(HOST_NEUTRAL_FILES)
    check_cli_invocation([QUERY_OPT, DEEP_ORCH, OPTIMIZE_CMD])
    check_reference_paths([QUERY_OPT, DEEP_ORCH, OPTIMIZE_CMD, SKILL])

    # Phase 1 framing contract in the main skill
    require(
        SKILL,
        "Decision card",
        "meta-question",
        "MECE",
        "section contract",
        "references/query-optimization.md",
        "references/deep-orchestration.md",
    )
    check_phase_one_block(SKILL)

    if FAILURES:
        print("query optimization contract check: FAIL")
        for failure in FAILURES:
            print(f"  - {failure}")
        return 1
    print("query optimization contract check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
