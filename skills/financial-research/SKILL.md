---
name: financial-research
description: "Use when the user asks about margin, cost of sales, COGS, gross margin, operating margin, EBITDA, working capital, unit economics, cost bucket, P&L, financial model input, comparable companies, filings, 10-K, or earnings call — any financial or operating-model research where terms, periods, denominators, scopes, and attribution confidence must stay explicit."
user-invocable: false
---

# Financial Research

Claim-safe research for financial and operating-model questions. The failure mode this skill prevents is not a missing source — it is a number that is real, cited, and **measured on a different basis than the claim it is used to support**.

Host-neutral: "host search tool", "host fetch tool", and "host file-read tool" mean whichever tools the running agent exposes. The plugin CLI is always:

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" <subcommand>
```

This skill is an overlay on the `research` skill, not a replacement. Run `/research:optimize` at level Q4 first, then the general research phases, with the controls below binding at every step. Full detail: `references/financial-controls.md`. Deliverable shape: `references/evidence-package-template.md`.

## When this skill fires

Trigger language: margin · cost of sales · COGS · oCOGS · gross margin · operating margin · EBITDA · working capital · unit economics · cost bucket · P&L · financial model input · comparable companies · filings · 10-K · earnings call · transformation cost · manufacturing cost · supply-chain cost · NPI.

If the question is financial, optimization level is **Q4** and depth is at least `standard`. Financial questions are never Q0–Q2: the basis controls are the work.

## 1. Term authority — before any use

Never use a financial label before defining it **and locating it in the financial statements**. Terms like NPI, oCOGS, transformation cost, manufacturing cost, and supply-chain cost are company-specific or analyst-specific constructs, not standard line items.

For each term, record: the definition being used, the source that defines it, and where it appears in the statements — or the explicit statement that it has **no single public line** and spans several.

A term that spans COGS, R&D, NRE, and capex cannot be sourced from one line, and treating a nearby line as its proxy is the most common way a financial research output goes wrong.

## 2. Measurement record — one per number

Every number carries a measurement record. A number without one does not enter the output.

| Field | Meaning |
|---|---|
| period | Fiscal quarter or year, explicitly labeled |
| currency | Reporting currency; note FX basis if translated |
| numerator | What is being measured |
| denominator | What it is measured against — revenue, COGS, units, ASP |
| scope | Consolidated vs parent-only vs segment vs product line |
| payer | Who bears the cost |
| beneficiary | Who captures the value |
| P&L location | Above or below gross profit; which line |
| reported vs adjusted | Never mixed without explicit labeling |

Two numbers may only be compared when every field matches or the mismatch is stated. Reported margin against adjusted margin is a presentation error, not a finding.

## 3. Attribution ladder

Rank every causal statement. The rung determines how the claim may be phrased.

| Rung | Definition | Permitted phrasing |
|---|---|---|
| 1. Disclosed contribution | The company states the contribution in a filing or on the record | "X contributed N bps" |
| 2. Derived estimate | Calculated from disclosed inputs with the arithmetic shown | "Implied N bps, derived from …" |
| 3. Directional evidence | Expert, analyst, or qualitative support for direction but not magnitude | "Directionally increases X; magnitude undisclosed" |
| 4. Unsupported hypothesis | Plausible mechanism with no evidence | Named as a hypothesis, never as a finding |

Evidence strength must be proportional to claim precision. A rung-3 source cannot support a rung-1 number.

## 4. Cost buckets and overlap groups

Define the bucket set before allocating anything, and declare which buckets can overlap so double counting is visible rather than silent.

- Name each bucket, its inclusion rule, and its exclusion rule.
- Declare overlap groups explicitly — e.g. procurement operations cost vs purchased-merchandise COGS category are different denominators and must not be summed.
- **Unknown sub-buckets remain unallocated.** A residual is a residual, not a bucket.
- Cost shares and margin-contribution ranges use separate columns and separate denominators. A gross-margin contribution range is not a cost share.

## 5. Mechanism tests

For any margin or cost movement, test which mechanisms actually explain it before attributing it:

product mix · pricing · sourcing economics · manufacturing automation · NPI and ramp cost · operating leverage / fixed-cost absorption · business-model migration (e.g. EMS → ODM → JDM).

State which mechanisms the evidence supports, which it rules out, and which remain untested. An unexplained movement is a finding.

## 6. Margin-layer discipline

Gross margin, operating margin, EBITDA, and working capital respond to different mechanisms. Keep them distinct:

- **Gross margin** — mix, pricing, conversion cost, material cost, absorption.
- **Operating margin** — gross margin plus opex leverage; R&D and SG&A sit here, not in COGS.
- **EBITDA** — adds back D&A; not comparable to operating margin across companies with different capital intensity.
- **Working capital** — inventory, receivables, payables; a cash-cycle effect, not a margin effect.

R&D is not an NPI-cost proxy. It sits below gross profit and covers broader engineering.

## 7. Source priority and duplicate control

| Priority | Source class | Use |
|---|---|---|
| 1 | Official filings and audited statements | Authoritative; cite directly |
| 2 | Direct expert transcripts (firsthand operators) | Mechanism and boundaries; scope-check the expert's visibility first |
| 3 | Analyst research | Estimates and models; label as estimate, never as guidance |
| 4 | AI auto-reports, lead sheets, compiled exports | **Discovery only.** Every promoted claim needs a source from a higher tier |

Duplicate control:

- Files with different hashes but identical normalized text are one source.
- Two AI auto-reports covering the same ground are **not independent corroboration**, however many times they repeat a claim.
- A filing and its audited statements are complementary, not duplicates.
- Analyst forecasts embedding different mix and adjustment assumptions are never averaged.

## 8. Scope rules and guardrails

Write the scope rules into the output before analysis, as a do-not list. Standing rules:

- Never present parent-only cost anatomy as consolidated.
- Never use one segment's margin as another segment's or as the group gross margin.
- Never combine reported and adjusted figures without labeling.
- Never present an analyst estimate as company guidance.
- Never turn a COGS *category* into an operating-cost bucket.
- Never validate a volume, unit, or share figure that no supplied source supports.
- Never count repeated auto-report claims as corroboration.

## 9. Certainty rubric

Quantitative findings carry High / Medium / Low certainty, consistent with `/research:analyze-plan` and `/research:analyze-run`:

- **High** — structured data, schema understood, deterministic formula or SQL, validations pass, no major assumptions.
- **Medium** — usable data with stated assumptions, partial schema ambiguity, or manual mapping.
- **Low** — OCR or PDF extraction, ambiguous grain or denominator, uncertain joins, failed validations, or missing critical inputs.

Certainty reflects input structure and validation status, not source credibility — source credibility is the tier. Report both.

Run calculations through the plugin rather than by hand:

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" table-profile <file>
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" analyze-plan --input <path> --question "..."
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" analyze-run --plan <analysis-plan.yaml>
```

## 10. Deliverable — evidence package

The output is an evidence package, not a narrative. Required sections: **Objective · Controlling evidence · Source register · Evidence/claim ledger · Scope rules · Deliverables · Known evidence ceilings**.

"Known evidence ceilings" is mandatory and states what the available sources **cannot** answer — the disclosure limits that bound every conclusion. Omitting it makes an incomplete answer look complete.

Template and worked column definitions: `references/evidence-package-template.md`.

## Related references

- `references/financial-controls.md` — full control detail, worked term-authority and bucket examples, reconciliation patterns.
- `references/evidence-package-template.md` — deliverable template.
- `../research/references/query-optimization.md` — Q4 optimization, decision card, section contracts.
- `../research/references/deep-orchestration.md` — query ledger, source and claim registers, reconcile step.
- `../research/references/credibility.md` — tiers and corroboration classes.
- `../research/references/quantitative-analysis.md` — analysis plan/run workflow and certainty rubric.
