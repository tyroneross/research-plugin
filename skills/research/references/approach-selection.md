# Select the research approach from the evidence job

Before sourcing, identify what the answer must establish and what inputs exist.
Choose the smallest approach that can establish that answer. Topic labels such
as “financial” or “engineering” select relevant controls, not an analytical
method. A definition can remain a direct lookup even when the topic is earnings.

## Selection procedure

1. State the decision or question, requested deliverable, supplied evidence,
   time/version scope, and explicit source/execution/save constraints.
2. Select a task shape and scientific methods through `method-routing.md`.
   Separately select zero or more ordered `approaches` from the table below.
3. Record one sentence explaining why the chosen approach fits the evidence
   job, which close alternative was rejected, and any missing inputs. Do this
   in the decision card; the CLI does not judge the quality of the rationale.
4. Validate the host's contract with `research.py route --request-file`.
   Inspect `approach_contracts` for inputs and completion rules. Obtain missing
   inputs, narrow the answer, or mark a gap before dependent execution.
5. Re-route when evidence changes the job. Preserve the earlier selection and
   reason. An expansion from one approach to another never expands permission.

Raw-query `approach_candidates` are tentative discovery hints, not selected
approaches. When `approach_selection_required` is true, the host must accept,
replace, or reject the suggestions by submitting an explicit `approaches` list
before sourcing. `[]` explicitly selects ordinary research. Unknown names,
duplicates and wrong types fail validation. Overrides win, including an empty
list. Routing remains read-only, does not enforce source completeness, and
does not claim that any research or validation was executed.

## Decision table

| Evidence job | Approach | Choose when | Avoid when |
|---|---|---|---|
| Establish a narrow fact or definition | `approaches: []` | A direct answer from permitted evidence suffices | Multiple mechanisms, decisions, or changing claims need reconciliation |
| Expand a credible-seeming idea into related useful guidance | `seeded_snowball` | A seed, fixed anchor and relevance boundary exist | The task needs representative prevalence or expert-consensus estimates |
| Explain quarterly results and outlook | `earnings_analysis` | Results, guidance, prior periods, management narrative or issuer-specific operating metrics need comparison | The user asks only what EPS means or requests a wording-only edit |
| Explain cost, margin or operating-model movement | `financial_mechanisms` | Competing mix, pricing, cost, absorption or investment explanations matter | A nearby accounting line is being used as an unsupported causal proxy |
| Compare decisions under explicit changed assumptions | `scenario_analysis` | Outcomes can be computed on a common baseline | Narrative scenarios lack quantitative inputs; use hypothesis framing instead |
| Find themes across a bounded source corpus | `thematic_synthesis` | Source-linked patterns, exceptions and dissent must be synthesized | The goal is fresh web discovery or a causal-effect estimate |
| Update previous understanding | `longitudinal_update` | Previous claims and new dated evidence can be reconciled | No prior state exists; start with collection or ordinary research |
| Fill gaps using firsthand testimony | `expert_interview` | Unresolved questions match an expert's actual visibility | Documentary facts suffice, or the expert lacks firsthand knowledge |

Scientific `methods` and these practical `approaches` are separate. Snowball
search is not an eligibility-controlled systematic review. Comparing a
management explanation with alternatives is not causal identification. A
calculated scenario is not an empirical forecast or a calibrated simulation.
Choose `review`, `causal`, `forecast` or `simulation` only when their own evidence
requirements are appropriate and obtainable.

## Earnings analysis

Load the sibling `financial-research` skill for basis and attribution controls.
Identify issuer, fiscal event and source cutoff before comparing numbers. Keep
actuals, prior-period results, prior guidance and consensus distinct; reconcile
scope and accounting basis. Compare prepared remarks with Q&A, new/discontinued
terminology, and operating indicators that support or challenge the narrative.
Treat unanswered questions as leads, never proof of concealment or a cause.

Separate reported fact, management view, external view and host inference.
For each material implication, record evidence, mechanism, affected entity,
time horizon, confidence, monitor and disconfirming evidence. Missing call
evidence means release-only coverage. Missing market evidence remains missing.

Use the [earnings pack helpers](../../financial-research/references/earnings-packs.md)
when a versioned brief and one-pager are requested. Do not create the whole pack
for a short answer or a bounded revision. Financial comparisons and every derived
number retain the existing calculation/verification requirements.

## Financial mechanisms

Define the metric and its statement location, then align periods, scope,
denominators and adjustments. List competing explanations before choosing one:
mix, pricing, sourcing, conversion cost, absorption, ramp costs, opex leverage,
or a business-model change where relevant. Test them against disclosed evidence.
Classify contributions as disclosed, derived, directional or hypothetical.
An unexplained residual stays unexplained. A statement about direction does
not justify a quantified contribution. Use the financial skill's attribution
ladder and cost-bucket controls; do not add a new financial taxonomy.

## Scenario analysis

Freeze a common baseline, forecast vintage, units, scope and accounting basis.
Connect demand, supply/capacity and cost assumptions to the outcome through
explicit formulas. Name what varies deliberately and what remains fixed. Compute
each case and reconcile its delta to those changes while constructing it.
Run boundary/reference checks and sensitivity tests for consequential assumptions.
Do not mix forecast vintages or invent driver weights to force a bridge.

Selecting this quantitative approach requires computation; a forbidden execution
setting remains a blocker, not permission to estimate mentally. If numbers or
models are unavailable, deliver an assumption/measurement plan with gaps. Label
computed scenarios as conditional outcomes, not probabilities or predictions.

## Thematic synthesis

Extract from each source before grouping across sources. Derive themes from
case-linked excerpts; record supporting sources, dissent, exceptions, irrelevant
sources and unresolved coverage. Match claim strength to source independence.
Mentions and repeated derivative reports do not establish consensus. Add
`methods: ["qualitative"]` when actual coding or qualitative analysis is needed;
ordinary source-faithful synthesis need not pretend to be a formal study.
Use the existing collection/synthesis references rather than a second pipeline.

## Expert interview

Map each unresolved question to the expert's role, tenure, geography and direct
visibility. Prioritize neutral questions, one ask each, before showing a proposed
answer or range. Define units, period and denominator for quantitative probes.
Separate firsthand experience, estimates and hearsay; preserve attributable
excerpts and limitations. Reconcile testimony against documentary evidence and
other independent sources. A question guide is only a plan until an authorized
interview actually happens. This selection never authorizes outreach or sending.

## Combining approaches

Order approaches by data dependency: an expert interview may fill a gap in an
earnings analysis; scenario analysis can use its reconciled inputs afterward.
Snowball discovery can find related mechanisms, but its source network does not
prove those mechanisms. For parallel work, disjoint evidence tasks and explicit
execution permission remain necessary. Use the existing orchestrator contract.

Example host selection:

```json
{
  "query": "Compare these supplied quarterly disclosures and test why margin changed; do not save",
  "task_shape": "compare",
  "methods": [],
  "approaches": ["earnings_analysis", "financial_mechanisms"],
  "source_policy": "supplied",
  "allowed_execution": "local",
  "overrides": {"persist": false}
}
```

Missing evidence changes the answer's status, not the permission settings or the
scope. Neither a route receipt nor an earnings-pack validator proves source truth.
