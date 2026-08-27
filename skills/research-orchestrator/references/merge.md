# Deterministic merge and reconciliation

Sort packets by `task_id`, then claims by `claim_id`. Ordering makes output repeatable; it does not resolve semantic disagreement.

Before comparing two claims, align:

1. entity identity;
2. event/data/publication/capture dates;
3. geography and population;
4. unit, denominator, and grain;
5. reported, adjusted, projected, or opinion basis;
6. source independence and citation lineage.

Create support, qualify, contradict, correct, or supersede relationships only after alignment. Preserve both original claims and both source observations.

Trust assessments are dated and topic-scoped. Keep these dimensions separate:

- citation grounding;
- uncertainty calibration;
- correction behavior, including observed opportunities to correct;
- declared opinion or bias framing;
- unsupported absolute language;
- nuance;
- discrepancy history.

A disclosed opinion may score high on framing transparency and low on independent corroboration. Unsupported words such as always or never raise review priority; they do not automatically make the underlying claim false.

Do not publish one composite trust score until the formula, version, component observations, smoothing, and minimum sample rule are recorded. A composite may rank follow-up candidates; it cannot determine truth or suppress dissenting evidence.

Place discovered conflict decisions in a separate append-only reconciliation manifest:

```json
{
  "run_id": "run-...",
  "initialized_contract_hash": "sha256:...",
  "reconciliations": [
    {
      "left_claim_id": "c1",
      "right_claim_id": "c7",
      "status": "preserved",
      "type": "contradiction",
      "basis_alignment": {
        "time": "aligned",
        "unit": "aligned",
        "denominator": "aligned"
      },
      "note": "Both evidence chains remain unresolved."
    }
  ]
}
```

The merge command rejects a manifest whose `run_id` or `initialized_contract_hash` differs from the initialized run. Claim IDs are scoped to their run in the graph, so two runs may both use `c1` without collapsing into one entity.

Every merge attempt snapshots the exact worker-result and reconciliation bytes under the external run directory using content-addressed filenames. The attempt records each input hash, task-to-claim mapping, source observation list, and original path. Later edits to a worker's scratch file do not alter the preserved merge inputs.
