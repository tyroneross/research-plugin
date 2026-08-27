# Verification (v0.2+)

Deterministic verification of atomic claims. The host extracts atoms; scripts verify.

A source observation is claim-eligible only when it has a validated content hash and either an exact locator or an explicit reason why a locator is unavailable. Legacy or incomplete observations may guide recapture work; they do not pass the merge gate as factual evidence.

## Quantitative acceptance rule

Numeric text matching only verifies transcription. It does not verify arithmetic.

A quantitative claim ships as fact only when `research.py calculate --spec <file>` creates a `passed` receipt containing:

- claim and run IDs;
- formula or query and its hash;
- unit, denominator, grain, and assumptions;
- exact input values and source observation IDs;
- plugin code hash, command, local runtime, and environment versions;
- result and output hash;
- at least one passing validation check.

Missing or ambiguous denominator, grain, input observation, or validation produces `inconclusive`. Failed checks produce `failed`. Corrections append a new receipt linked with `correction_of_receipt_id`; they never overwrite the earlier receipt.

## Pattern

```
Notes body → Extractor (LLM) → [atoms] → Router (code) → Verifier (code) → Report
```

Based on the FActScore / FacTool decompose-extract-retrieve-verify pattern, stripped to minimums.

## Atom types

```json
{
  "atom_id": "a1",
  "type": "numeric | symbolic | code | citation",
  "claim": "CoT improves GSM8K accuracy from 17.9% to 58.1%",
  "needs": ["benchmark_or_citation"],
  "source_refs": ["https://arxiv.org/abs/2201.11903"]
}
```

- **numeric** — a quantity, unit, comparison, or ratio.
- **symbolic** — an equation, closed-form, identity, or inequality.
- **code** — a Python snippet whose behavior is claimed.
- **citation** — an attribution ("Wei et al. 2022 introduced CoT") verifiable via OpenAlex.

## Routing (`research.py verify`)

| Type | Verifier | Dep |
|---|---|---|
| `numeric` | Regex-parse quantities + units, retrieve top-5 Raw chunks via FTS5, bootstrap CI via stdlib `statistics` + `random.choices`. | stdlib |
| `citation` | `urllib.request` → `api.openalex.org/works?filter=doi:<doi>` or `search=<title>`. Confirm existence + year. | stdlib |
| `symbolic` | `sympy.simplify(lhs - rhs) == 0`. Falls back to `inconclusive` if `sympy` not installed. | sympy (opt) |
| `code` | v0.3: `subprocess` + `tempfile` + resource limits (Docker if available). v0.2 marks `inconclusive`. | stdlib (+docker opt) |

## Verifier output

Each atom produces `~/dev/research/verifier-log/<slug>/<atom_id>.json`:

```json
{
  "atom_id": "a1",
  "type": "numeric",
  "claim": "CoT improves GSM8K accuracy from 17.9% to 58.1%",
  "verdict": "passed | failed | inconclusive",
  "evidence": "Retrieved chunk #3 from arxiv.org excerpt states: '...58.1% on GSM8K...'",
  "artifact": "verifier-log/prompting.chain-of-thought/a1.stdout",
  "cmd": "python -c 'import statistics; ...'",
  "confidence": "✅ | ⚠️ | ❓",
  "timestamp": "2026-04-17T14:22:00Z"
}
```

## Entry-level rollup

After all atoms run, update entry frontmatter:

```yaml
verification:
  run: 2026-04-17T14:22:00Z
  atoms: 4
  passed: 3
  inconclusive: 1
  failed: 0
```

And combined with corroboration (see `source_scoring.md`), set the entry `confidence` field.

## Inline markers

When an atom fails or is inconclusive, `verify` appends a marker to the claim in Notes:

- Passed: no change.
- Inconclusive: `{claim: "...", atom_id: a1} ⚠️ unverified`
- Failed: `{claim: "...", atom_id: a1} ❌ verifier says X instead`

## Running

```bash
python research.py verify <slug>           # runs all atoms
python research.py verify <slug> --atom a1 # single atom (for debugging)
python research.py verify <slug> --dry-run # extract atoms, don't run verifiers
```

## What this is not

- Not a theorem prover. Lean/Coq are overkill for the claims we actually make.
- Not a full fact-checking service. Judgment calls (contested interpretations, qualitative claims) still need a host agent or human reviewer.
- Not a safety sandbox for arbitrary code. v0.3 code execution assumes the user ran the research themselves; don't use it to verify untrusted third-party code.

## Extending

New atom types go in the router. Pattern:
1. Add to the `atoms` JSON schema the extractor prompt uses.
2. Add a case to `research.py verify`'s routing table.
3. Add a verifier function that returns `{verdict, evidence, artifact, confidence}`.
