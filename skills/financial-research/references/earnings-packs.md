# Build and validate an earnings output pack

Use these helpers when earnings research needs a versioned chat brief, a separate
one-pager handoff, and a shared claim ledger. The host researches and reviews;
local Python creates packs and checks their consistency. It never fetches sources,
calls a model, or establishes financial truth from an attestation.

This is the new `research.earnings.v1` contract, reconstructed from the WorkWiki
workflow. It does **not** claim compatibility with the missing WorkWiki scripts or
their historical schema 1.1 packs. WorkWiki remains unchanged.

## Create, populate, review, validate

The three named scripts are thin entry points into `research.py`; mutations stay
in that canonical script. Run from any directory using the scripts' absolute paths.
These examples assume the repository root:

```bash
python3 scripts/init_earnings_output.py \
  --company "Example Systems" --ticker EXAMPLE --fiscal-year 2026 --quarter Q2 \
  --as-of 2026-08-04 --period-end 2026-06-30 --earnings-date 2026-08-04 \
  --source-cutoff 2026-08-04T20:00:00+00:00 --json

python3 scripts/validate_earnings_output.py /absolute/path/to/2026-08-04-v1 \
  --scaffold --json

python3 scripts/validate_earnings_output.py /absolute/path/to/2026-08-04-v1 --json

python3 scripts/revise_earnings_output.py /absolute/path/to/2026-08-04-v1 \
  --scope financial-data --claim-id C1 --change-note "Correct the revenue input" --json
```

The same interfaces are `research.py earnings-init`, `earnings-validate`, and
`earnings-revise`. No new slash commands are required. `--help` lists the flags.

Default output: `<research-content-root>/earnings/<company-slug>/fy<year>-q<N>/<as-of>-v<N>/`.
`--base-dir` changes only the initializer's output root. No SQLite/index creation
is needed by these helpers. They do not automatically save a research-library
entry; use the existing Phase 6 save flow when requested.

Version allocation selects one greater than the highest existing version for the
requested date, then uses exclusive directory creation and retries collisions.
Existing files/directories consume their version number. Date strings are strict
`YYYY-MM-DD`; fiscal years are integers from 1900 through 9999. Slugs use ASCII
lowercase letters/digits separated by hyphens, with at most 100 characters.

The initializer writes a **scaffold**, not research findings. Populate it before
complete validation. Use a source cutoff with an explicit UTC offset. For a
historical pack, supply the historical cutoff explicitly; the default is now.

## Five required files

| File | Purpose |
|---|---|
| `manifest.json` | Event identity, source cutoff, review and revision provenance |
| `source-ledger.tsv` | Exact numeric values, basis, claims and dependencies |
| `one-pager-content.json` | Structured analytical handoff bound to ledger IDs |
| `one-pager-content.md` | Readable content handoff |
| `webex-brief.md` | Separate copy-ready communication |

Symlinked company/fiscal output directories are rejected before pack allocation;
an existing output ancestor cannot redirect writes outside the chosen root.

Sources also need retained evidence files, normally under `captures/`. Derived
metrics need calculation receipts, normally under `calculations/`. References must
be relative paths within the pack. Symlinks, special files, and files over 4 MiB
are rejected. Keep small, permitted, source-faithful captures. Paths never trigger
network access. Referenced captures/receipts are included in the pack-review hash.

The committed [synthetic example](../../../tests/fixtures/earnings-v1/2026-08-04-v1/manifest.json)
shows a complete v1 pack. It is test data, not a real company's earnings or an
assertion that a live source was checked.

## Manifest contract

Required fields; unknown fields fail:

| Field | Contract |
|---|---|
| `schema_version` | Exactly `research.earnings.v1` |
| `company`, `ticker` | Non-empty strings |
| `fiscal_year`, `quarter` | Integer year; `Q1`, `Q2`, `Q3`, or `Q4` |
| `period_end`, `earnings_date` | ISO dates, required for complete validation |
| `as_of`, `version` | ISO date and positive integer matching the directory name |
| `created_at`, `source_cutoff` | ISO timestamps with offsets; cutoff cannot follow creation |
| `source_state` | `release_only` or `call_included` |
| `latest_period_check` | `{status, checked_at, note}`; complete packs require `passed`, a timestamp within cutoff, and an evidence note |
| `review` | `{status, reviewer, reviewed_at, input_hash}` |
| `revision` | `null` for initial packs; generated provenance for revisions |

Completed packs require `period_end <= earnings_date <= cutoff date <= as_of`.
Sources must be published before access, and accessed within the cutoff. A
`call_included` pack requires a current transcript source. Current transcript
evidence cannot be labeled `release_only`. Release-only passes include a coverage
warning; missing call evidence is never represented as a negative call finding.

## Ledger contract

The TSV header must exactly match this order:

```text
claim_id kind statement value unit period scope basis status material evidence_class source_ids locators validation formula denominator grain receipt depends_on
```

The file uses actual tabs. `source_ids`, `locators`, and `depends_on` are JSON
values inside TSV cells; use a TSV writer rather than constructing rows by hand.

| Field | Rule |
|---|---|
| `claim_id` | Unique; letter followed by up to 79 letters/digits/underscores/dots/hyphens |
| `kind` | `metric`, `statement`, `quote`, or `inference` |
| `statement` | Precise, non-empty source claim or labeled inference |
| `value` | Finite decimal string for metrics; empty for other kinds |
| `unit`, `period`, `scope`, `basis`, `denominator`, `grain` | Explicit for metrics; use `not_applicable: <reason>` where appropriate |
| `status` | `reported`, `guidance`, `consensus`, `derived`, or `estimated` |
| `material` | Literal `true` or `false` |
| `evidence_class` | `reported_fact`, `management_view`, `external_view`, or `inference` |
| `source_ids` | Non-empty JSON list of known source IDs |
| `locators` | JSON object mapping every cited source ID to its exact locator |
| `validation` | `passed`, `source_only`, `gapped`, `failed`, or `pending` |
| `formula`, `receipt` | Required for a completed derived metric; receipt is a pack-relative file |
| `depends_on` | JSON list of upstream claim IDs; unknown IDs and cycles fail |

Material or published claims must be `passed` or `source_only`. A validated claim
cannot depend on an unvalidated claim. Guidance must be `management_view`;
consensus must be `external_view`; inference must remain labeled `inference`.
Discovery-only, stale, undated and conflicted evidence cannot support published
or material claims. Preserve those leads separately or leave the finding gapped.

Derived metrics reuse the existing `research.py calculate` receipt format. Register
source observations and calculate through the existing tools, then copy the
receipt into the pack. Receipt claim ID, source observation IDs/capture hashes,
formula, unit, denominator, grain, input/output hashes and exact result must agree.
The validator reruns the formula and every recorded check. A copied `passed`
string or a recomputed hash cannot make incorrect arithmetic pass. This does not
prove that an input was correctly transcribed or that the chosen formula answers
the research question; those remain review responsibilities.

Numeric inputs, formula constants and final numeric results use the same finite
decimal bounds (adjusted exponent magnitude at most 100). Arithmetic failures,
including intermediate Decimal overflow in formulas or checks, produce a
structured validation failure rather than a traceback.

## Structured content contract

`one-pager-content.json` requires `metadata`, `headline`, `financial_highlights`,
`financial_drivers`, `strategic_highlights`, `implications_slide`, `sources`,
`footnotes`, and `content_gaps`. The initializer emits the complete skeleton;
the synthetic example supplies populated values.

- `metadata` exactly matches the manifest's company/ticker/fiscal year/quarter/
  period end/earnings date. `headline` has `title` and `takeaway` strings.
- Complete packs need one through five financial highlights. Fewer than three
  requires an explicit content gap. Each highlight has `claim_id`, `label`,
  `display_value`, `display`, `comparison`, `insight`, `unit`, `period`, `scope`,
  `basis`, `status`, `source_ids`, and `footnote_ids`. Basis/source fields must
  match its unique metric claim. Unsupported comparisons say `Not sourced`.
- `display` has `scale` (`1`, `1000`, `1000000`, or `1000000000`, as strings),
  integer `decimals` from 0 through 6, `prefix`, and `suffix`. Divide the exact
  decimal by scale, round using decimal `ROUND_HALF_UP`, retain the declared
  decimal places, and concatenate prefix/value/suffix. `$1.255B` therefore
  displays as `$1.26B` at two decimals. No binary floating-point arithmetic.
- Financial drivers and every strategic/implication subsection are lists of
  analytical items: `{text, claim_ids, evidence_class, confidence, source_ids}`.
  Confidence is `high`, `medium`, or `low`. Inferences also require `mechanism`,
  `time_horizon`, `monitor`, and `disconfirming_evidence`; quoted claims require
  `speaker`, `role`, and `context`. Items must match their linked claims' evidence
  classes and source IDs. Optional market-data sections stay empty when unsourced.
- A source has `source_id`, `citation_text`, `url`, `path`, `document_type`,
  `role`, `tier`, `tier_rationale`, `publication_date`, `accessed_at`,
  `recency_status`, `upstream_source_ids`, `capture_path`, `content_hash`, and
  `observation_id`. At least one of URL/original path is non-empty. Capture hashes
  use `sha256:<64 lowercase hex>` and must match retained bytes. Observation IDs
  are unique; use actual registered observations for calculator inputs.
- Source document types: `release`, `filing`, `presentation`, `transcript`,
  `expert`, `market`, `other`. Source roles: `PRIMARY-DISCLOSURE`, `DIRECT-EXPERT`,
  `INDEPENDENT-ANALYSIS`, `DERIVATIVE-SUMMARY`, `AI-DISCOVERY`. Tiers are T1–T4;
  recency is `current`, `recent-context`, `stale`, `undated`, or `conflicted`.
- Footnotes have unique `footnote_id`, `text`, and known `source_ids`.
  `content_gaps` is a list of distinct, non-empty strings.

The brief starts with the structured title in bold. Proof bullets use exactly
three spaces, `•`, and one tab. A blank line cannot separate a bold headline
from its proof bullets. Remove `EARNINGS_DRAFT` markers from both Markdown files.
No arbitrary prose-to-number inference is performed: the structured numeric
handoff is checked mechanically; prose fidelity, quote wording, comparison text,
causality and the controlling takeaway require the recorded content review.

## Review and failure behavior

`earnings-validate` is read-only. Once all other checks pass, a pending review
produces exit 2 and reports `review_input_hash`. After **actually** reviewing
the sources, prose, interpretation and arithmetic method, the host/human records
`review.status: passed`, its non-empty identity in `reviewer`, an offset timestamp
in `reviewed_at`, and that exact hash in `input_hash`. Rerun complete validation.
The script never manufactures this review. The review is a local assertion,
not an authenticated independent audit.

The hash binds the manifest except its `review` object, all four deliverables,
and referenced capture/receipt files. Any change to those bytes invalidates the
review. Changing irrelevant unreferenced files does not. Complete validation
does not modify the manifest, calculate new receipts, or mark claims verified.

Exit 0 means the requested operation succeeded; exit 2 means invalid input or
validation failure. `--json` writes one JSON object to stdout, with errors and
warnings in separate lists for validation. Without it, errors/warnings go to
stderr. `status: scaffold` never means `pass` or source verification.

## Revision rules

The parent path is explicit; no hidden “latest” selection occurs. It must pass
complete validation before copying. The new date defaults to the parent's date
and cannot precede it. The parent remains unchanged. All copied files are regular
files; nested symlinks and special files fail. Failed writes remove only the
new directory allocated by that invocation.

| Scope | Inputs and invalidation |
|---|---|
| `formatting`, `wording` | No changed claim IDs; preserve ledger, sources, basis, dependencies, and inference controls. Display/prose fields may change; a protected fingerprint detects changes to evidence or ledger claim meaning. |
| `interpretation` | Require one or more `--claim-id` inference claims. Set those claims and all transitive dependents to `pending`. |
| `financial-data` | Require one or more metric claim IDs. Set those claims and all transitive dependents to `pending`; rerun affected calculations. |
| `source-refresh` | Invalidate every claim and reset the latest-event check. Update cutoff, sources and receipts as needed. |

Every revision resets the **pack review** to pending, including wording and
formatting. Evidence validation can carry forward while review of changed prose
remains necessary; no unchanged browsing needs to be repeated. Old receipts are
retained in the copied pack, but pending claims cannot use them as a passed
publication gate. Revision provenance records parent path/hash, scope, note,
affected IDs, invalidated IDs, and any protected fingerprint. Parent paths are
historical locators; validation does not need access to the original parent.
