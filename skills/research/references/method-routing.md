# Research method routing

Use the requested outcome and evidence needed to justify it. A discipline is a source/method hint, not a route: psychology may need qualitative coding, measurement or experiments; economics may need causal inference, forecasting or simulation; engineering may need optimization, experiments or formal verification.

## Contract and precedence

1. Read the user's intended output and explicit constraints.
2. Classify `task_shape` and an ordered `methods` list in the host. No external classifier API is needed. An empty methods list means ordinary information research.
3. Put explicit user controls in `overrides`; put host classification in the top-level fields. Overrides win over host classification, which wins over tentative keyword defaults.
4. Run `research.py route --request-file <request.json> --json`. Raw `route --query "..." --json` is a provisional hint, not a semantic decision.
5. Review the receipt's reasons, confidence, capability gaps and stage requirements. If ambiguous, record an alternative in the decision card. Resolve consequential missing input before dependent execution.

```json
{
  "query": "Estimate whether the intervention caused an improvement",
  "task_shape": "explain",
  "methods": ["causal"],
  "domain": "psychology",
  "available_capabilities": ["python"],
  "overrides": {"depth": "standard", "persist": false, "source_policy": "supplied", "allowed_execution": "local"}
}
```

Supported fields: `query`, `task_shape`, `methods`, `depth`, `workflow`, `verification`, `domain`, `source_policy`, `computation`, `persist`, `allowed_execution`, `independent_tasks`, `available_capabilities`, and `overrides`. Unknown fields and invalid values fail validation. `overrides` accepts routing fields except `query`; booleans must be JSON booleans.

| Control | Values / meaning |
|---|---|
| Task shape | `lookup`, `compare`, `survey`, `explain`, `collect` |
| Workflow | `general`, `collection`, `synthesis`, `quantitative` |
| Depth | `light`, `standard`, `deep`; effort only |
| Verification | `standard`, `adjudication`; contested claims require a contradiction ledger and evidence review, not default debate |
| Source policy | `supplied`, `local`, `web`, `mixed`; host access rules still apply |
| Computation | `required`, `on_demand`, `forbidden`; quantitative work upgrades on-demand to required; forbidden work stays blocked |
| Execution | `plan_only` (default), `local`, `agents`; availability does not grant permission |
| Persistence | Boolean, independent of effort; explicit false wins at every depth |

The command is read-only and never launches workers, searches or scripts. It returns `planned` or `blocked_missing_input`; neither means work has been executed. Capability declarations are host assertions. Missing data and assumptions must still be checked against each stage's `required_inputs`. The route is not a sandbox or a completion validator.

## Methods and core structures

| Method | Core structure | Completion evidence |
|---|---|---|
| `review` | Dependency pipeline | Eligibility protocol, screening ledger, study-level extraction, appraisal; justified statistical pooling if used |
| `qualitative` | Dependency pipeline | Case-linked excerpts, explicit analytic method, themes and exceptions |
| `measurement` | Dependency pipeline | Operational definitions, reliability/validity checks and uncertainty |
| `causal` | Dependency pipeline | Estimand, identification assumptions, executed estimator and robustness tests |
| `forecast` | Dependency pipeline | Event/horizon/cutoff, probability, resolution rule; scoring after outcomes resolve |
| `simulation` | Evaluation loop | Calibrated environment, seeds, computed metrics, sensitivity and external-validity limits |
| `hypothesis` | Evaluation loop | Candidate lineage, novelty and falsification criteria; empirical support kept separate |
| `experiment` | Evaluation loop | Protocol, controls, actual observations and deviations; a proposed protocol is only a plan |
| `optimize` | Evaluation loop | Fixed objective/evaluator, constraints, baseline and tested improvement |
| `formal` | Evaluation loop | Formal statement and accepted proof-checker artifact |
| `archival` | Dependency pipeline | Provenance, chronology, corroboration and unresolved contradictions |

For ordinary information tasks, use a single loop. Comparison, survey and collection can use bounded fan-out and merge only when `independent_tasks >= 2` and `allowed_execution: agents`; choose worker count from available capacity and budget, not entity count alone. Define disjoint ownership, a shared schema and merge checks using the existing research-orchestrator contracts. Keep dependent reasoning with one owner. The returned four structures are recommendations, not claims of universal benchmark superiority.

Ordered methods create dependent stages, e.g. `qualitative` → `hypothesis` → `experiment` → `causal`. For changing task shapes (survey → compare), create separate route requests and connect their output/inputs in the section contracts or existing orchestrator task DAG. Re-route when new evidence changes the task; preserve the previous route and reason.

## Validation and escalation

Use the lightest structure that meets the method's evidence requirements. Depth source counts are planning guidance for open research, not quotas for a supplied dataset, a proof or an experiment. Apply the method's evidence rules and record unavailable source lanes instead of padding citations. Add independent extraction, a challenger or a bounded search lane only for a named gap. Adjudication checks source independence, dates, definitions and conflicting evidence; agreement between agents is not validation.

All derived quantities load `quantitative-analysis.md`. Existing scripts come first; reviewed Python handles unsupported calculations. Validate formulas, units, denominators, reference cases and uncertainty. Preserve executed artifacts and failed checks. The route's `calculation_contract` lists the required evidence.

Keep route confidence (`clear`, `tentative`, `needs_input`) separate from claim certainty. After execution, report each section as executed, validated within scope, inconclusive or blocked, backed by artifacts. Do not label an architecture validated merely because routing succeeded. Method profiles are informed by the linked research assessments, with evidence strength and limitations retained there:

- [Task-shape assessment](../../../docs/proposals/2026-09-07-use-case-research-routing.md)
- [Discipline and architecture evidence](../../../docs/proposals/2026-09-07-discipline-research-methods.md)
