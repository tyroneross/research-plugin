# Seeded, relevance-bounded snowball research

Use when the user brings an idea, tip, article, or expert recommendation and wants related useful material or more comprehensive guidance. Validate the starting claim, then expand through relationships that help answer a fixed anchor question. An apparently knowledgeable person is a discovery lead; credibility must be assessed for the specific claim.

This is a host-executed sourcing overlay for General Research, not a new CLI method or a systematic review. Keep depth, source access, computation, execution permission, and persistence independent. Do not add `snowball` to the route contract's `methods` list; use the supported task shape and methods, and record this overlay in the decision card and section contracts.

## 1. Validate the seed before expanding

Record the original tip, attribution and source locator when available. Separate the author's exact claim from the user's paraphrase and the host's interpretation. If only a recollection is available, record that limitation; never invent a quotation or citation.

Check terminology, underlying mechanism, applicability, source expertise for this claim, date/version when relevant, and credible counter-evidence. Search outside the seed's citation network too. Treat the seed's truth and its usefulness for discovery as separate questions. Named techniques need not constitute recognized principles, and popularity does not establish correctness.

Give the seed a provisional disposition with evidence:

- **Supported within scope** — evidence supports the specific premise and its conditions; keep those conditions attached.
- **Reframed** — the tip points at something useful but its terminology, generality, or mechanism needs correction; retain the original and explain the correction before expanding.
- **Unverified** — evidence is missing or inaccessible; allow only explicitly exploratory discovery and do not turn the tip into established guidance.
- **Contested or contradicted** — preserve both evidence chains; investigate the disagreement or expand from an explicitly corrected premise, never from the disputed premise as fact.

Do not make credibility a binary gate based on reputation. If the premise cannot be established, say what remains uncertain and what evidence would resolve it.

## 2. Fix the anchor and expansion budget

Write the question this research must answer, intended use, in-scope implementations, and exclusion boundary. For example: “Which principles make this framework's hooks reliable?” Record a seed disposition, source/time budget from the chosen depth, and a stopping rule before expansion.

Select additional independent seed sources within that budget: an original or official treatment of the mechanism, an independent implementation or architecture treatment, and relevant failure/security/reliability evidence where available. These are source roles, not a quota or evidence of independence. If the budget or source policy permits only one source, report the limitation and do not claim corroboration. Supplied-only research never silently becomes web research.

Extract concepts and claims before expanding. Reuse source IDs, claim IDs, exact locators, and the credibility classes in [credibility.md](credibility.md) and the registers in [deep-orchestration.md](deep-orchestration.md).

## 3. Expand through labeled relationships

Work outward in rounds, comparing candidate branches before spending the next round's budget. A round is one bounded pass over the current frontier. Prioritize unresolved section-contract questions, independent evidence, and counter-evidence over merely similar content.

Keep two kinds of expansion distinct:

- **Concept expansion** — find governing principles, prerequisites, failure modes, implementation mechanisms, alternatives, generalizations, and analogies. Record why each connection answers the anchor and whether the connection is source-stated or host-inferred.
- **Citation expansion** — follow a source's references backward and verified citing sources forward when the host has access. Inspect the citing passage: a citation may criticize or merely mention a claim. Record the actual relationship; never infer influence, endorsement, or independence from a link or search snippet. An unavailable citation index is a coverage gap, not evidence that no citing sources exist.

For each candidate, record its parent concept/source, labeled relationship, expected contribution to the anchor, applicability, and include/exclude/defer decision with a reason. Collapse duplicates and synonyms while preserving source wording and provenance. Search for alternatives and failures outside the connected seed cluster to reduce anchoring.

Use relevance labels:

| Relevance | Admission rule |
|---|---|
| Direct | Answers the anchor or explains a necessary mechanism |
| Conditional | Helps only under a named implementation condition; state that condition |
| Analogy | Suggests a hypothesis across contexts; does not transfer evidence automatically |
| Out of scope | Requires a different question or has no concrete use for this anchor; exclude or defer |

“Radius” is an editorial judgment of conceptual distance. Parent principles, immediate implications, and adjacent disciplines are useful groupings, not measured distances or mandatory stages. Record the rationale. URL hop depth is separate: a direct prerequisite may be several links away; an unrelated page may be one hop away.

When following page links under a research-orchestrator run, retain its [traversal policy](../../research-orchestrator/references/traversal.md) and `traversal-record` checks. Conceptual relevance never overrides URL depth, domain, page, byte, time, or access limits. Search-discovered sources remain within the overall research budget; do not use fresh searches to evade traversal restrictions.

## 4. Check recurrence without claiming consensus

Assess support for each specific claim under matching applicability conditions. Distinguish a source that mentions a concept from one that recommends it, tests it, disputes it, or merely cites another source. Keep source quality, relevance, extraction confidence, and claim corroboration separate.

Apply the existing independence test before assigning `SUPPORTED`. Record shared authors, organizations, citations, and upstream evidence. Derivative articles and repeated vendor claims remain one evidence family for corroboration; unknown lineage is not assumed independent. Preserve exceptions and contradictions rather than voting them away.

Report recurrence as “independently supported in the sources inspected,” with the sources and conditions enumerated. Source presence establishes neither repeated endorsement nor expert consensus. Do not rank consensus or general frequency from this purposive sample. If the user needs a defensible prevalence estimate, define a population, eligibility and sampling protocol, and denominator as a separate review task. Compute any reported counts or ratios through the existing quantitative tools or reviewed Python; never estimate them from prose.

## 5. Stop and report why

Review the frontier after each round and record new applicable concepts, changes in independent support, contradictions, remaining gaps, and excluded branches. Choose a saturation window proportional to depth; two consecutive rounds with inspected sources but no material additions is a useful default, not a statistical guarantee.

Stop a branch when it drifts outside the anchor. Stop the run when section completion rules are met and the chosen saturation window yields no new applicable concepts, independent support, or material counter-evidence, or when the declared budget/access limit is reached. Never claim saturation from failed retrievals, empty snippets, or an inaccessible source lane. Budget exhaustion and source/access gaps mean bounded or incomplete coverage, with the unresolved frontier retained. Saturation applies only to the inspected scope, never to the whole literature.

## 6. Deliver and preserve the reasoning

Lead with the corrected or supported premise and the useful guidance. Include:

1. **Seed assessment and anchor** — original claim, disposition, corrected framing, and implementation scope.
2. **Concept map** — a source-backed relationship table or a rendered map grouping direct, conditional, and analogy connections. Keep parent/child IDs, relationship labels, rationale, applicability, and evidence references in one canonical record. Use Diagram Intelligence for a rendered process/data-flow map when available; report a fallback honestly.
3. **Evidence and applicability** — concept, actual claim, supporting/opposing source IDs and locators, relationship to anchor, condition, evidence families/independence rationale, corroboration class, and confidence. Label host inferences.
4. **Reading list** — prioritize by relevance and evidence quality; annotate what each source adds, its limits, and whether it is a discovery lead or supporting evidence.
5. **Coverage and stop record** — section-contract status, conceptual versus citation coverage, round results, excluded/deferred branches, stop reason, and remaining gaps. Do not describe this as a consensus ranking.

Scale the record to the depth; a light run can use a compact table. These are host-maintained research records, not new validated JSON fields. When persistence is enabled, put the seed, concept/evidence table, reading list, and stop record in `Notes`; retain permitted source extracts with locators and capture dates in `Raw`; save through the existing Phase 6 flow. Honor explicit no-save instructions.

Compact record (expand source IDs into the existing source register):

| Concept / actual claim | Parent / relationship / basis | Relevance / applicability | Supporting and opposing sources / locators | Independence / corroboration / confidence |
|---|---|---|---|---|
| `<concept ID and precise claim>` | `<parent ID; prerequisite, etc.; source-stated or inferred>` | `<direct, conditional, analogy; conditions>` | `<source IDs and exact passages>` | `<evidence families and rationale; existing credibility class>` |

## Hooks example (illustrative, not sourced guidance)

Given a tip that “byte-level checks and exact matching are the two principles of hooks,” first test that terminology against the target framework and underlying mechanism. A correction could distinguish techniques from governing principles; do not assume that correction without evidence.

For the anchor “How do we make hooks reliable in this plugin system?”, comparison semantics and callback ordering may be direct concerns. Retry handling and idempotency belong only when the implementation actually retries or performs side effects. Event sourcing may be deferred when answering it would require changing the anchor to distributed-system architecture. Source each admitted claim and condition during the real run.
