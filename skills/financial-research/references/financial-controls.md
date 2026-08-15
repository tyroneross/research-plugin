# Financial Research Controls

Full detail behind the `financial-research` skill. Host-neutral: any tool reference means the **host search tool**, **host fetch tool**, or **host file-read tool** — whichever the running agent exposes.

## Term authority

Financial labels used in operating-model work are constructs, not line items. Before a term appears in any claim, fill this record:

| Field | Example |
|---|---|
| term | `oCOGS` (other cost of goods sold) |
| definition in use | Procurement, planning, vendor management, inventory management, and logistics operating cost |
| defining source | The source that supplied this definition, with locator |
| statement location | Whether it maps to a disclosed line, part of a line, several lines, or nothing public |
| proxy risk | What a reader might wrongly substitute for it |

Worked examples of the failure this prevents:

- **NPI / design / industrialization** spans COGS (ramp inefficiency), R&D, NRE recovery, and capex. There is no single recurring public line. Using reported R&D as an NPI proxy overstates NPI and imports unrelated engineering spend.
- **Transformation / conversion cost** is direct labor plus manufacturing overhead. It is not "COGS minus materials" unless the company discloses that materials figure on the same scope and period.
- **Supply-chain cost** conflates two different things: the *operating cost* of running procurement (an expense) and the *purchased-merchandise* COGS category (a cost of goods). They have different denominators and must never be summed.
- **Manufacturing cost** in a parent-company statement is a factory-input split. It is not the consolidated cost of sales.

If a term has no public line, say so in the output. "No complete public split exists" is a finding, not a gap in the research.

## Measurement record — expanded

Each field, and what goes wrong when it is missing:

| Field | Failure when omitted |
|---|---|
| period | Comparing a quarter to a fiscal year as if they were the same basis |
| currency | Translating at an unstated FX rate; comparing across reporting currencies |
| numerator | "Margin" that turns out to be markup |
| denominator | A percentage of revenue compared against a percentage of COGS |
| scope | Parent-only presented as consolidated; one segment presented as the group |
| payer | Attributing a cost to a party that does not bear it |
| beneficiary | Attributing value capture to a party that does not receive it |
| P&L location | Placing an opex item inside gross margin, or vice versa |
| reported vs adjusted | Mixing GAAP gross margin with adjusted operating margin on one chart |

Record it once per number, at extraction time. Recovering the basis later, from a number already in a table, is usually impossible.

## Attribution ladder — application

Rung determines phrasing, and phrasing determines what a reader is entitled to do with the claim.

- **Rung 1 (disclosed contribution)** requires the company's own statement of the contribution. Cite the filing or transcript with an exact locator.
- **Rung 2 (derived estimate)** requires every input to be disclosed and the arithmetic to be shown or reproducible from an analysis artifact. Show the calculation; do not present a derived number as disclosed.
- **Rung 3 (directional evidence)** supports direction only. An expert saying sourcing "helps a lot" supports "sourcing is a material driver" and does not support "sourcing contributes 300 bps."
- **Rung 4 (unsupported hypothesis)** appears only in a hypotheses section, never in findings.

A revenue-equals-100 waterfall from an expert is a **directional gross-margin allocation**, not a cost share. Converting one into the other silently changes both the numerator and the denominator.

## Cost buckets and overlap groups

Bucket definition record:

| bucket | includes | excludes | denominator | overlaps with |
|---|---|---|---|---|
| Manufacturing / conversion | Direct labor, manufacturing overhead, test, integration | Materials, procurement operating cost | % of revenue | — |
| NPI / design / industrialization | Ramp inefficiency in COGS, NRE, design cost | Ongoing platform R&D | Spans COGS + R&D + capex | Manufacturing (ramp), R&D |
| Supply-chain execution | Procurement, planning, vendor management, logistics operating cost | Purchased-merchandise COGS category | % of revenue | Purchased merchandise (different denominator — do not sum) |

Rules:

1. Buckets are declared before allocation, not fitted to the numbers afterward.
2. Every overlap is named. An undeclared overlap becomes double counting the moment anyone adds the columns.
3. Unknown sub-buckets stay unallocated and are shown as a residual with that label.
4. A sensitivity ("a 10% reduction in the disclosed conversion base is about 25 bps of revenue") is a bounded arithmetic statement on a disclosed base — not an estimate of the bucket's size.

## Mechanism tests

For each observed movement, run through the mechanisms and state supported / ruled out / untested:

| Mechanism | Evidence that supports it | Common false positive |
|---|---|---|
| Product mix | Segment or product revenue shares moving with margin | Attributing mix effects to pricing |
| Pricing | Realized price or ASP series | List price mistaken for realized price |
| Sourcing economics | Component cost or supplier-terms evidence | Analyst BOM residual read as a measured split |
| Manufacturing automation | Labor content, cycle time, yield evidence | Any conversion-cost decline assumed to be automation |
| NPI / ramp | Program timing against margin timing | Ramp cost read as structural cost |
| Operating leverage | Fixed-cost absorption against volume | Volume growth credited to efficiency |
| Business-model migration | Contract-model or design-ownership change | Model migration inferred from margin alone |

A modeled value-add residual (for example, "BOM 80% / manufacturer value-add 20%") is useful for dollar-scale sensitivity. It is **not** a measured split of manufacturing, NPI, and supply-chain cost, and must never be presented as one.

## Reconciliation patterns

Financial reconciliation is basis reconciliation. Before calling two figures contradictory, check in this order: period → scope → reported/adjusted → denominator → currency → definition. Most disagreements resolve at one of those steps, and the resolution is itself a finding worth stating.

Only what survives all six is a genuine contradiction. Record both sides with tier, date, and locator; state which one the conclusion leans on and why; never average them.

Full reconcile-step mechanics: `../../research/references/deep-orchestration.md`.

## Known evidence ceilings

Every financial research output ends with what the sources cannot answer. Typical ceilings:

- No public model-specific margin split by business model.
- No complete public cost split across the declared buckets.
- No generation-specific or product-specific reported margin.
- Best available cost breakdown is parent-only, not consolidated.
- A volume or unit-count range that no supplied source supports.

Stating the ceiling is what makes the rest of the package usable. An output without one implies a completeness the evidence does not have.
