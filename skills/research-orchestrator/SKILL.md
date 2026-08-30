---
name: research-orchestrator
description: Plan and coordinate source-backed research with parallel evidence tasks, bounded second- or third-level link traversal, deterministic quantitative receipts, contradiction-preserving merge, and append-only provenance. Use for requests such as "research this deeply", "use parallel research agents", "follow links two levels", "audit the sources", or "verify the math".
compatibility: Requires Python 3 and the research plugin CLI. Optional Apple Vision OCR adapter requires macOS.
user-invocable: false
---

# Research Orchestrator

Create one research contract before sourcing. Keep reasoning in the host and enforcement in deterministic scripts. Never call an external model API from a bundled script.

## Hard gates

1. State the ask, intent, decision outcome, success criteria, and practical consequence of a wrong answer.
2. Separate confirmed facts, hypotheses, assumptions, and requested tests.
3. Give every hypothesis at least one observable falsifier and state what a falsification would change.
4. Define good and poor sources for this topic before retrieval. Include primary/original, independent corroboration, counter-evidence, temporal/currentness, and gap lanes.
5. Require every quantitative factual claim to cite a passed deterministic calculation receipt. Mark missing, ambiguous, or failed calculations `inconclusive`.
6. Keep one canonical writer. Parallel workers return immutable result packets; the coordinator validates and reconciles them.
7. Preserve contradictions, corrections, opinion framing, and uncertainty. Never average conflicting claims or collapse them into one smooth narrative.
8. Persist source representations and results outside the plugin repository under the configured research content and index roots.

## Workflow

### 1. Frame

Build a JSON run contract using [contracts.md](references/contracts.md). Include:

- objective, intent, and intended outcome;
- decision card and section coverage contracts;
- hypotheses with falsifiers;
- source quality policy for this topic;
- disjoint task ownership;
- merge strategy;
- bounded traversal policy;
- required calculation and trust evidence.

Validate and initialize it:

```bash
python3 "$RESEARCH_PLUGIN_ROOT/research.py" run-validate --contract run-contract.json
python3 "$RESEARCH_PLUGIN_ROOT/research.py" run-init --contract run-contract.json \
  --actor-type host-agent --actor-id coordinator --host "$RESEARCH_HOST" \
  --session-id "$RESEARCH_SESSION_ID" --tool-version "$RESEARCH_TOOL_VERSION"
```

### 2. Assign

Use the host's native agent mechanism when parallel work is authorized and available. Do not encode vendor or model names in the contract. Assign by capability and bounded section:

- source discovery and primary evidence;
- independent corroboration and counter-evidence;
- temporal/version history;
- quantitative validation;
- synthesis or audit.

Give each worker one generated task packet. Require the run ID, initialized contract hash, `task_id`, claim IDs, source observation IDs, an explicit cross-run reuse list, exact locators, limitations, and calculation receipt IDs for quantitative claims.

When parallel execution is unavailable, execute the same task packets serially. The persisted contract and merge rules stay identical.

### 3. Traverse

Follow [traversal.md](references/traversal.md). Start at depth 2. Use depth 3 only when depth 2 exposes a specific unresolved evidence gap and the contract records the reason.

Use the host's browser/search capability for public pages. Record each representation through `source-record`. Do not add a background crawler or bypass authentication, permissions, robots rules, or paywalls.

After inspecting links on each captured page, pass every accepted and rejected candidate to `research.py traversal-record --manifest <file> --run-id <id>`. The command applies contract depth/domain/page/byte/time limits and stores rejection reasons before the host opens the next accepted page.

### 4. Extract and route

Use native text first. Use deterministic parsers next. Use OCR for image-only or low-text pages. Use a vision-capable host only for layout, charts, handwriting, formulas, or failed OCR.

On macOS, the optional local adapter is:

```bash
swift scripts/local_ocr.swift /absolute/path/to/image.png > ocr-source.json
python3 "$RESEARCH_PLUGIN_ROOT/research.py" source-record \
  --manifest ocr-source.json --run-id "$RUN_ID"
```

The adapter emits a source-record-compatible manifest with route, runtime, engine revision, confidence, input hash, and output hash. Add a page/range locator when the image came from a larger document. OCR confidence measures extraction quality, not source truth.

### 5. Verify quantities

Create one JSON calculation spec per quantitative claim. Include formula, unit, denominator or an explicit `not_applicable` explanation, grain, assumptions, exact input values, source observation IDs, and validation checks.

```bash
python3 "$RESEARCH_PLUGIN_ROOT/research.py" calculate --spec calculation.json \
  --actor-type script --actor-id deterministic-calculator --host local
```

Accept the claim as quantitative fact only when the command returns zero and the receipt status is `passed`. A matching hash proves identity and a rerun proves reproducibility; neither proves that the formula answers the right question. Keep formula-choice review separate.

### 6. Merge

Follow [merge.md](references/merge.md). Run:

```bash
python3 "$RESEARCH_PLUGIN_ROOT/research.py" run-merge \
  --contract contract.json --result task-a.json --result task-b.json \
  --reconciliation reconciliation.json \
  --output merged.json
```

Omit `--reconciliation` only when no conflicts were discovered. The reconciliation file must name the run ID and the `contract_hash` returned by `run-init`; see [merge.md](references/merge.md).

Resolve scope, time, unit, denominator, geography, and reported-versus-adjusted basis before comparing values. Preserve unresolved contradictions with both evidence chains.

### 7. Persist and audit

Save the final three-layer entry with the run ID and explicit actor provenance. Rebuild source indexes and run the doctor:

```bash
python3 "$RESEARCH_PLUGIN_ROOT/research.py" save --file entry.md --run-id "$RUN_ID" \
  --actor-type host-agent --actor-id coordinator --host "$RESEARCH_HOST"
python3 "$RESEARCH_PLUGIN_ROOT/research.py" source-index
python3 "$RESEARCH_PLUGIN_ROOT/research.py" doctor --json
```

Report doctor findings as coverage gaps. Never convert missing provenance into inferred metadata.

## Failure handling

- Missing source representation: unsupported claim.
- Failed or partial extraction: preserve the capture and lower extraction confidence.
- Ambiguous denominator, grain, or join cardinality: calculation is inconclusive.
- Missing worker: mark its section uncovered; do not let another result silently claim coverage.
- Worker conflict: preserve both claims and add reconciliation status.
- Host capability unavailable: execute serially or select another local adapter; keep the contract vendor-neutral.
