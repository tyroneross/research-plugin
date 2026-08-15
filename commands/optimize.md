---
description: "Convert an initial prompt into a claim-safe research contract — decision card, meta-questions, MECE sub-question groups, section contracts"
argument-hint: "<raw-request-or-transcript>"
allowed-tools: "Bash, Read"
---

Optimize `$ARGUMENTS` into a research-ready contract. Do **not** start researching — this command produces the specification the research run will execute.

Host-neutral: any tool reference means the **host search tool**, **host fetch tool**, or **host file-read tool** — whichever the running agent exposes.

Load `skills/research/references/query-optimization.md` from this plugin and follow it. Summary of the required output:

First, classify depth to choose an optimization level:

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" depth "$ARGUMENTS"
```

`light` → Q0–Q1, `standard` → Q2–Q3, `deep` → Q4. Raise one level for multi-decision requests, quantitative claims that will enter a model, or contested definitions. Raise to Q4 for any financial or operating-model question and load the `financial-research` skill instead of continuing here.

Then emit, in order:

1. **Input classification** — four registers, kept separate: USER-PROVIDED FACTS · WORKING HYPOTHESES · REQUESTED TESTS · UNSUPPORTED ASSUMPTIONS.
2. **Decision card** — decision · what we must know by the end · flagship question(s) · required scope · required basis (unit + denominator) · minimum useful answer · what changes with the answer · requested output format.
3. **Meta-question(s)** — one per decision. **Never merge distinct questions.** If two parts could be answered by different evidence and one could be true while the other is false, they are separate meta-questions and stay separate.
4. **MECE sub-question groups** — themes named after the decision components; these become the output's section headings. Scope, direct answer, drivers, boundaries, and confidence are evidence checks *inside* each theme, never headings.
5. **Section contracts** — one table per meta-question, columns: `Section | Exact question | Evidence required | Expected output | Completion rule`. Completion rules must be objectively checkable.
6. **Readiness score** — 0–24 across decision, scope, time/period, definitions, evidence expectations, metrics/basis, comparisons, output requirements. Report before and after.
   - ≥ 18: proceed.
   - 12–17: proceed with assumptions written explicitly into the contract.
   - < 12: ask at most three targeted questions — **unless** the user said "just research it" or equivalent, in which case state the assumptions and proceed without asking.
7. **Assumptions carried forward** — every unsupported assumption the run will operate under, listed so the user can correct it mid-run.

Preserve the user's intent, hypotheses, uncertainties, and requested output format throughout. Optimization sharpens the specification; it never narrows what was asked for.

Hand the section contracts to `/research:research` (or the `research` skill's Phase 2) as the source plan. They are checked off at synthesis as the coverage summary.

If no request was given, ask the user what they want optimized.
