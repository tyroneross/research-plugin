# Evidence Package Template

Deliverable shape for financial and operating-model research. Copy the headings verbatim; fill every section or state why it is empty.

Host-neutral: any tool reference means the **host search tool**, **host fetch tool**, or **host file-read tool** — whichever the running agent exposes.

---

# Evidence package

## Objective

One paragraph: the decision this package informs, what it produces, and what it tests. Carried from the decision card in `../../research/references/query-optimization.md`.

## Controlling evidence

Bulleted list of the sources that carry the conclusion — filings, audited statements, transcripts, analyst research — with dates. Name the register files that hold the full inventory.

## Source register

| source_id | title | source_date | path_or_url | tier | exact_locator | independence |
|---|---|---|---|---|---|---|
| S01 | | | | T1 | | primary/original |
| S02 | | | | T4 | | discovery lead sheet only — every promoted claim requires another source |

Rules: `exact_locator` is mandatory and specific (page, statement, table, section). Discovery-only sources are labeled as such and can never corroborate a claim. Sources restating a shared upstream claim are marked non-independent.

## Evidence ledger

| evidence_id | source_ids | evidence_type | statement | exact_locator |
|---|---|---|---|---|
| E01 | S01,S02 | reported metric | | |
| E02 | S01 | calculated bridge | | arithmetic in `<artifact>` |
| E03 | S03 | disclosure limit | | |

`evidence_type` values in use: `reported metric` · `adjusted metric` · `calculated bridge` · `calculated metric` · `scope reconciliation` · `business-model definition` · `cost anatomy` · `disclosure limit` · `evidence gap` · `analyst model` · `analyst estimate` · `expert estimate` · `sensitivity` · `source-quality limit` · `operating-model synthesis` · `accounting bridge`.

Every calculated row names the artifact holding the arithmetic. Every estimate row names whose estimate it is.

## Claim register

| claim_id | statement | evidence_ids | attribution rung | corroboration class | certainty | basis |
|---|---|---|---|---|---|---|
| C01 | | E01,E02 | 2. derived estimate | SUPPORTED | High | period · currency · numerator · denominator · scope |

Attribution rung and certainty are separate axes: a rung-1 disclosed figure extracted from a low-quality scan can still be Medium certainty.

## Scope rules

The do-not list, written before analysis. Standing entries plus any specific to this run:

- Reported and adjusted margins are never combined without explicit labeling.
- Parent-company cost anatomy is never presented as consolidated.
- One segment's margin is never used as another's or as the group gross margin.
- Analyst estimates are never presented as company guidance.
- AI auto-reports are discovery maps only.
- Cost shares and margin-contribution ranges use separate columns and denominators.
- Unknown sub-buckets remain unallocated.

## Deliverables

Inventory of what this package produced — workbook, slides, analysis artifacts, QA manifest — with paths and a one-line description each.

## Known evidence ceilings

What the available sources cannot answer, stated plainly. One bullet per ceiling. This section is mandatory; an empty one means the ceilings were not looked for.
