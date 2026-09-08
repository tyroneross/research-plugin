# Research run contract

Use JSON so deterministic validation can reject missing fields before research starts.

```json
{
  "objective": "Answer one bounded research question",
  "intent": "Explain why the answer is needed",
  "outcome": "Name the decision or artifact this informs",
  "success_criteria": ["Every published claim has captured evidence"],
  "wrong_answer_consequence": "State the practical cost of a false conclusion",
  "decision_card": {
    "decision": "Name the decision this research changes",
    "use": "Explain how the decision maker will use the answer"
  },
  "source_policy": {
    "good": ["primary records", "independent methods", "dated evidence"],
    "poor": ["uncited aggregation", "hidden framing", "unsupported absolutes"],
    "coverage_lanes": ["primary", "independent", "counter-evidence", "currentness"]
  },
  "hypotheses": [
    {
      "hypothesis_id": "h1",
      "statement": "A testable statement",
      "falsifiers": ["An observable result that would reject it"],
      "decision_consequence": "What changes if rejected"
    }
  ],
  "tasks": [
    {
      "task_id": "t1",
      "section": "primary-evidence",
      "question": "One disjoint sub-question",
      "depends_on": []
    }
  ],
  "section_contracts": [
    {
      "section": "primary-evidence",
      "completion_criteria": ["At least one captured primary source and one stated gap"]
    }
  ],
  "merge_strategy": {
    "ordering": "task_id-then-claim_id",
    "single_writer": true,
    "preserve_contradictions": true
  },
  "traversal": {
    "max_depth": 2,
    "max_pages": 30,
    "max_bytes": 20000000,
    "max_seconds": 600,
    "allowed_domains": ["example.org"],
    "robots_policy": "respect-fail-closed"
  }
}
```

The contract describes roles and capabilities. Host and model identity belong in run provenance, not task semantics.
Contradictions discovered during execution cannot be frozen into this immutable contract. Record them later in a separate reconciliation manifest bound to both the run ID and the initialized contract hash.

Every task result uses this minimum shape:

```json
{
  "run_id": "run-...",
  "initialized_contract_hash": "sha256:...",
  "task_id": "t1",
  "claims": [
    {
      "claim_id": "c1",
      "claim_kind": "factual",
      "statement": "One atomic claim",
      "evidence_observation_ids": ["obs-..."],
      "contradicts": [],
      "calculation_receipt_id": null
    }
  ],
  "source_observation_ids": ["obs-..."],
  "reused_observation_ids": [],
  "limitations": []
}
```

Use `claim_kind: quantitative` for computed numbers. That kind requires a passed `calculation_receipt_id`.
Every result must echo the initialized run and contract hash. List intentional evidence reuse from another run in `reused_observation_ids`; undeclared cross-run observations fail merge and declared reuse becomes an explicit graph edge.

## Connect financial, quantitative and qualitative evidence

Keep `claim_kind` separate from evidence modality. A computed result still uses `claim_kind: quantitative` and requires a passed calculation receipt. A quotation or interpretation does not become a computed fact simply because its evidence is financial. Add optional `evidence_types` from `financial`, `quantitative`, `qualitative` to describe the material.

A claim can carry explicit `connections` to another claim in the same merge:

```json
{
  "target_claim_id": "financial-claim",
  "relationship": "contextualizes",
  "rationale": "Interview accounts provide context for costs; they do not identify the causal effect.",
  "evidence_observation_ids": ["obs-interview"],
  "basis": {
    "entity": "Example company",
    "period": "Interview period differs from filing period",
    "population": "Interview sample versus whole company",
    "measure": "Reported experience versus operating costs"
  },
  "alignment": "different"
}
```

Allowed relationships are `supports`, `contextualizes`, and `qualifies`. Use the existing symmetric `contradicts` and reconciliation protocol for conflicts. Targets must exist in the merge; self-links are rejected. Connection evidence must belong to the source or target claim. Rationale, all four basis fields, and `alignment: matched|different|unknown` are required. State unknowns explicitly.

The coordinator judges connections from source content; scripts validate structure and references. Every connection is recorded as an **asserted relationship**, not causal proof or a validated statistical association. Similar topics, matching company names or periods do not justify automatic links or pooling. Different/unknown basis remains visible. Source statements, modality labels, basis and rationale are preserved on append-only connection nodes. Repeated identical assertions deduplicate; changed assertions remain separate history.

Export with `graph-export --run-id <run-id>`. The graph connects claims through these relationship nodes and keeps source observations, numbers, calculation receipts and corrections reachable. Use JSON for complete basis/properties and Mermaid for a readable map. No embedding service or vector database is required.
