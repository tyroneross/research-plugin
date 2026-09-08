# Discipline-informed research methods and agent architecture

Implementation follow-up: the route contract and method profiles are now implemented; execution tools remain capability-dependent. See [method routing](../../skills/research/references/method-routing.md). The assessment below records the evidence and proposal at research time.

Status: research assessment and proposed design, 2026-09-07. No runtime changes.

## Decision

**Add a research-method layer to the previous five task shapes, and add an explicit experiment/evaluation feedback loop to the execution structures.** The earlier lookup/compare/survey/explain/collect proposal describes information work adequately, but does not specify how new conclusions become justified. Forecasting, causal inference, measurement, and experimentation need different contracts even when all produce an explanatory report.

The strongest transferable pattern is **an agent proposes work, while evidence outside the agent's prose determines success**: observed outcomes, statistical estimators, source passages, a simulator, a test suite, or a proof checker. Some systems demonstrate useful multi-agent designs; their results do not establish that a team is always superior to one agent with equivalent tools and budget.

Use disciplines to discover relevant methods and source standards. Route on the actual question and available evidence. Economics can require forecasting, causal inference, simulation, or archival work; psychology can require experiments, qualitative analysis, or measurement validation.

## Scope and assessment method

Decision: which additional research methods and execution patterns should this personal research plugin support?

Three questions guided the pass:

| Question | Evidence required | Completion rule |
|---|---|---|
| Which disciplinary methods need distinct contracts? | Methods guidance and original research across psychology, economics, engineering, and adjacent fields | Describe each method's question, evidence, output, and failure criterion |
| Which agent architectures actually exist and work? | Original system papers, architecture descriptions, evaluations, and limitations | Identify an implemented example or explicitly mark the architecture as proposed; distinguish benchmark, experimental, and deployment evidence |
| What should this plugin adopt? | Fit against existing task shapes, source/claim contracts, computation, and host constraints | Specify routing signals, minimum contract, capability fallback, and adoption order |

This was a targeted cross-disciplinary evidence review, not an exhaustive systematic review. Searches covered supporting systems and counter-evidence; publication/version dates were checked where available. Full architecture/results sections were inspected for PaperQA2, CausalAgent, Co-Scientist, Frontier-Eng, and the forecasting pipeline. Other entries rely on accessible abstracts, original reports, or official method documentation as labeled below. No systems were installed, run, or independently replicated.

Evidence labels are local assessment categories, not a standardized grading scale:

- **Demonstrated:** measured experiments, executable/formal results, or reported operational deployment in a bounded setting.
- **Benchmarked:** evaluated on defined tasks or datasets; external generalization remains uncertain.
- **Prototype:** implementation/demo exists, with insufficient comparative evidence for the proposed use.
- **Adaptation:** a recommended plugin architecture inferred from a method or component; no direct agent validation found in this pass.

## Research methods worth distinguishing

### 1. Systematic evidence review and meta-analysis

Psychology, medicine, education, and economics ask: “Across eligible studies, what does the evidence support?” This requires a search protocol, inclusion/exclusion decisions, study-level extraction, risk-of-bias assessment, and justified synthesis. A search-agent answer is not a systematic review merely because it has many citations. PRISMA is reporting guidance, not a quality certification. [PRISMA](https://www.prisma-statement.org/prisma-2020), [Cochrane](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-07).

**Architecture:** protocol-controlled pipeline → screening queue → extraction → appraisal → synthesis; optional statistical pooling only when the studies and measures support it. Partition records for throughput, but preserve eligibility decisions and unresolved screening cases.

**Evidence:** ASReview uses researcher feedback and active learning to prioritize screening, with simulation evaluations and user testing. It is an evaluated ML workflow, not an LLM research team. PaperQA2 uses adaptive paper search, evidence gathering, citation traversal, and answer generation; its ablations support iterative retrieval on its literature tasks. Neither result proves autonomous end-to-end meta-analysis. [ASReview](https://www.nature.com/articles/s42256-020-00287-7), [PaperQA2](https://arxiv.org/abs/2409.13740).

**Plugin contract:** eligibility protocol, databases and query dates, deduplication keys, study rather than paper identity, screening ledger, exclusion reasons, extracted estimates/basis, bias judgments, and an evidence synthesis. Grade: **benchmarked components; adapted complete workflow**.

### 2. Qualitative and interpretive research

Psychology, sociology, anthropology, and UX ask: “How do people describe and make sense of this experience?” Evidence is interview material, field notes, or documents, interpreted under an explicit analytic approach.

**Architecture:** source-linked excerpt extraction → initial coding → cross-case theme development → analyst review of interpretations and exceptions. Preserve participant/case context when batching. Record whether the method uses a stable codebook or reflexive interpretation; reviewer agreement is not a universal definition of qualitative validity.

**Evidence:** CoTI explicitly separates Instructor, Thematizer, and CodebookGenerator roles. Its revised paper reports evaluation primarily on 12 heart-failure patient transcripts, with comparison to senior-investigator reference outputs. It reports favorable similarity but only marginal gains from adding junior investigators in an exploratory collaboration study. This supports assistance for a bounded thematic-analysis task, not replacement of qualitative researchers. [CoTI](https://arxiv.org/abs/2512.16063).

**Plugin contract:** analytic approach, unit of analysis, excerpt locators, code definitions/revisions, case context, alternative interpretations, and theme-to-evidence links. Grade: **small benchmark; broader method adaptation**.

### 3. Measurement and construct validation

Psychology and organizational research ask: “Does this instrument measure the intended construct?” Economics and product analytics have analogous questions about proxies and indices. This is different from calculating a score.

**Architecture:** define construct → map items/measures → audit data and scoring → run statistical validation → assess scope of interpretation. One agent can coordinate specialist statistical tools; discussion among agents cannot establish validity.

**Evidence:** Wulff and Mata evaluate semantic embeddings for relationships among psychological items, scales, and labels, including out-of-sample comparisons. This supports a computational component for construct mapping; it is not a validated autonomous psychometrics agent. [Original study](https://www.nature.com/articles/s41562-024-02089-y).

**Plugin contract:** construct definition, target population, instrument/version, observed responses, reliability and validity questions, missingness, scoring, and out-of-sample checks. Grade: **benchmarked component; adapted agent workflow**. Generated respondent answers cannot establish empirical instrument validity.

### 4. Causal inference and impact evaluation

Economics, epidemiology, psychology, and policy ask: “What effect did intervention X have on outcome Y?” A plausible mechanism or correlation does not identify that effect.

**Architecture:** specify treatment/outcome/population and target effect → state identification assumptions → analyze data → estimate → sensitivity/refutation checks. A shared-state dependent pipeline is a better starting point than independent narrative workers.

**Evidence:** DoWhy explicitly separates model, identify, estimate, and refute. It is a causal-analysis library, not an agent architecture. CausalAgent implements data-processing, causal-structure-learning, and reporting agents with shared state and tool calls. Its full paper presents a Sachs dataset demonstration and places quantitative causal effect estimation in future work. Do not advertise it as proven autonomous policy evaluation. [DoWhy](https://www.pywhy.org/dowhy/v0.9.1/user_guide/effect_inference/index.html), [CausalAgent full paper](https://arxiv.org/html/2602.11527v1).

**Plugin contract:** estimand, causal graph or design rationale, data-generating assumptions, confounders, estimator, uncertainty, robustness tests, and identification limitations. Grade: **agent prototype; established computational workflow**. If identification is unsupported, return an association analysis or a research design with the limitation explicit.

### 5. Forecasting

Economics, policy, business, and operations ask: “What is likely to happen by a specified date?” Success requires eventual scoring against outcomes, not merely citations supporting a persuasive scenario.

**Architecture:** define event and resolution → retrieve time-bounded evidence → estimate probabilities with explicit base rates → optionally ensemble forecasts → preserve a forecast snapshot → score after resolution.

**Evidence:** Halawi and colleagues implement retrieval, probabilistic reasoning, and aggregation using a trimmed mean, with prompts and a fine-tuned component selected on validation data. Their evaluated system approaches aggregate competitive human forecasting on the tested binary questions. This is evidence for a particular pipeline, not universal superiority or a reason to use debating agents. ForecastBench provides an ongoing evaluation framework; its documentation cautions that human and later model rounds can involve different questions. [Forecasting study](https://arxiv.org/abs/2402.18563), [ForecastBench](https://www.forecastbench.org/explore/).

**Plugin contract:** event, horizon, resolution source/rule, information cutoff, probability or distribution, base-rate reference, update history, and scoring rule. Grade: **benchmarked**. A scenario without an assigned probability is a different artifact.

### 6. Simulation and mechanism design

Economics, social science, and operations ask: “What happens in this modeled system if we change incentives, rules, or constraints?” Agents may be the simulated population rather than research assistants.

**Architecture:** calibrated environment → interacting agents → intervention/scenario runs → deterministic metrics → comparison with observed data and sensitivity checks.

**Evidence:** AI Economist co-trains economic agents and a social planner using two-level reinforcement learning, with results in specified simulated economies. This is not a team of LLM analysts. Interview/survey-grounded generative agents have also been evaluated against held-out human responses; that is narrower than proving population-level policy validity. A separate psychometric audit reports that synthetic respondents can fail distributional and downstream checks despite plausible answers. These studies use different populations and tasks, so they establish boundaries rather than directly contradicting each other. [AI Economist](https://arxiv.org/abs/2108.02755), [Grounded individual simulations](https://arxiv.org/abs/2411.10109), [Counter-evidence](https://arxiv.org/abs/2608.14606).

**Plugin contract:** modeled population, environment, behavioral assumptions, calibration data, random seeds, interventions, observed-vs-synthetic labels, and external validity checks. Grade: **demonstrated in bounded simulations; mixed evidence for human substitution**. Treat simulation outputs as model-conditional findings.

### 7. Hypothesis generation and theory development

Biology, psychology, and other sciences ask: “What new explanation is plausible, distinct from prior work, and testable?” Novelty and empirical support must remain separate.

**Architecture:** generate multiple hypotheses → retrieve supporting and challenging evidence → rank for novelty/testability → refine → propose discriminating experiments. Candidate generation can be parallel; one ledger preserves lineage and rejected alternatives.

**Evidence:** Google's Co-Scientist uses generation, reflection, ranking, evolution, proximity, and meta-review agents under a supervisor. The 2026 Nature paper reports agent ablations, expert assessment, and wet-laboratory validation in selected biomedical applications. This is meaningful support for a specialized multi-agent architecture. Its debate/ranking component helps select hypotheses; empirical experiments, not tournament scores, support the resulting scientific claims. [Co-Scientist](https://www.nature.com/articles/s41586-026-10644-y).

**Plugin contract:** hypothesis, mechanism, provenance, novelty search, competing explanations, predicted observations, falsifiers, and next test. Grade: **demonstrated with domain experts in selected biomedical applications**. Transfer to psychology or economics remains a proposed adaptation.

### 8. Experimental research and active experimentation

Psychology tests interventions on behavior; chemistry and engineering manipulate physical or computational systems. The key question is: “Which experiment should we run, and what does its outcome establish?”

**Architecture:** hypothesis → protocol/design → permitted execution → measurement → analysis → next experiment. Keep protocol changes and exploratory follow-ups distinct from the original confirmatory test.

**Evidence:** Coscientist combines a planner, web/documentation modules, code execution, and laboratory tools, demonstrating experimental planning and reaction optimization. Its authors describe human assistance/oversight in the experimental work. These are chemistry demonstrations, not proof of autonomous human-subject experimental research. [Coscientist](https://www.nature.com/articles/s41586-023-06792-0).

**Plugin contract:** intervention, controls, experimental unit, outcomes, protocol/version, execution authority, measurements, analysis plan, and stopping rule. Grade: **demonstrated in chemistry; adaptation elsewhere**. Without an authorized execution environment, deliver an experiment plan and mark it unexecuted.

### 9. Engineering design and optimization

Engineering and operations research ask: “Which feasible design best meets the objective under these constraints?” A literature comparison alone cannot answer this when performance depends on implementation.

**Architecture:** propose candidate → run fixed evaluator/simulator → check feasibility → record score → select/refine candidates. One evolving candidate or a bounded population can use this same loop.

**Evidence:** AlphaEvolve couples code generation with automated evaluators and evolutionary selection; Google reports operational use of resulting algorithms. Frontier-Eng evaluates iterative optimization across engineering tasks with fixed verifiers, feasible starting artifacts, and constrained budgets. The latter is benchmark evidence, not a field certification. [AlphaEvolve](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/), [Frontier-Eng](https://arxiv.org/abs/2604.12290).

**Plugin contract:** editable candidate, immutable evaluator, baseline, objective, hard constraints, test scenarios, resource budget, and evaluation receipts. Grade: **reported deployment plus benchmark support**. A simulator validates against its model; physical transfer requires separate evidence.

### 10. Formal and deductive research

Mathematics and formal software verification ask: “Does the claim follow from these assumptions?” A vote among models is not a proof.

**Architecture:** formalize statement → search proof/counterexample → invoke proof checker → repair → return verified artifact or failure.

**Evidence:** AlphaProof combines a language model, reinforcement learning, and Lean proof search. The published IMO account includes formally checked outputs and important setup limitations, including human formalization of contest problems. This supports machine-checked search, not an ordinary LLM's ability to certify informal claims. [AlphaProof](https://deepmind.google/blog/ai-solves-imo-problems-at-silver-medal-level/).

**Plugin contract:** precise proposition, assumptions, formal encoding, checker/version, proof artifact, and correspondence between the formal and original statements. Grade: **demonstrated formal results**. No checker available means an unverified derivation.

### 11. Historical and archival reconstruction

History, legal history, and institutional research ask: “What happened, when, and what do surviving records support?” This requires document provenance, dates, identity resolution, and awareness of gaps in the archive.

**Architecture:** corpus intake → layout/transcription checks → targeted extraction → entity/event chronology → cross-source interpretation. Preserve original wording and date uncertainty rather than smoothing them into a narrative.

**Evidence:** Chronos supports customizable historian workflows; its Chronos-Extract component was benchmarked on historical source corpora. The measured claim concerns targeted extraction, not reliable autonomous historical explanation. [Chronos, revised August 2026](https://arxiv.org/abs/2604.03553).

**Plugin contract:** archive/document identifiers, author and date provenance, transcription confidence, quoted evidence, event links, contradictions, and missing-record boundaries. Grade: **benchmarked extraction; adapted reconstruction workflow**.

## Revised core structure for this plugin

Keep the earlier five labels as **task shapes**, not the complete research taxonomy. Add a versioned method profile and one explicit feedback structure:

```text
user objective + supplied evidence + constraints
    → task shape(s): lookup / compare / survey / explain / collect
    → method: review / qualitative / measurement / causal / forecast /
              simulation / hypothesis / experiment / optimize / formal / archival
    → evidence contract + evaluator + available tools
    → execution: single loop / dependency pipeline / bounded fan-out /
                 propose–evaluate–revise loop
    → findings + validation status + unresolved gaps
```

The fourth execution structure is semantically distinct from a retrieval loop: its next action depends on measurements or executable evaluation of a candidate. It can share the same task graph implementation. Human review is a control applied where method and authorization require it, not another automatic agent role.

The profile needs `method`, `question_type`, `required_inputs`, `assumptions`, `evidence_unit`, `validation_method`, `completion_rules`, `available_capabilities`, and `allowed_execution`. Existing source/claim/calculation/run records remain authoritative. A method-specific artifact references them rather than duplicating provenance.

Separate **architecture evidence** from **current-run verification**. For example: “optimization loop has benchmark support” does not mean “this candidate has passed its tests.” Useful run states include `planned`, `executed`, `validated_within_scope`, `inconclusive`, and `blocked_by_missing_input`.

## Detection rules and examples

Explicit user method selection wins. Otherwise infer the claim the user wants to establish and check whether the required evidence exists. Domain words only supply context.

| User request | Method route | Required distinction |
|---|---|---|
| “What does research say about this intervention?” | evidence review | Narrative review vs protocol-based systematic review |
| “Pool these studies' treatment effects” | review + quantitative meta-analysis | Compatible effects, uncertainty, study dependence |
| “Why do customers describe onboarding as confusing?” with interviews | qualitative | Interpretation of accounts vs causal effect |
| “Does our engagement score measure engagement?” | measurement | Construct validity vs convenient calculation |
| “Did the new onboarding increase retention?” | causal | Treatment effect vs before/after association |
| “Will retention exceed our target next quarter?” | forecast | Probability with horizon and resolution |
| “What if competitors change pricing in response?” | simulation | Model-conditional scenarios vs forecasts |
| “Suggest mechanisms explaining this unexplained result” | hypothesis | Candidate explanation vs established fact |
| “Design a test that separates the two explanations” | experiment, planning stage | Protocol vs executed result |
| “Find the fastest implementation that stays correct” | optimize | Performance objective plus immutable correctness checks |
| “Prove this invariant always holds” | formal | Finite testing vs formal proof |
| “Reconstruct how the policy changed from these records” | archival | Record-supported chronology vs invented continuity |

Generic “why” is not enough to select causal inference. Inspect whether the user requests an intervention effect, a mechanism, or an interpretation of reported experience. Mixed methods become stages: interviews → hypotheses → experiment design → causal analysis. Without suitable data, return the appropriate protocol or evidence gap rather than claiming to have completed the empirical study.

## Adoption recommendation

**Greenfield target:** typed method contracts with pluggable evaluators and explicit evidence states. This supports additional disciplines without adding one agent team per discipline.

**Best fit for this plugin:** retain the current CLI and evidence store. Add method instructions and routing metadata before adding execution engines. Build the protocol, ledger, and validation mechanics locally; reuse available statistical tools and host capabilities without introducing provider SDKs.

1. **Adopt first:** evidence review, qualitative analysis, causal-analysis planning, forecasting records, and archival research. They extend existing collection/synthesis/provenance capabilities. Empirical execution stays conditional on data and tools.
2. **Add bounded execution:** optimization and experiment loops using local tests or simulations. Enforce fixed evaluators, objective/constraint separation, and budgeted iterations.
3. **Keep specialized:** hypothesis tournaments, calibrated social simulation, psychometric validation engines, and formal provers. Provide contracts and fallbacks; activate specialized tools only when a real use case warrants them.

Do not copy architecture names as proof of implementation. Prompting one agent to play three roles does not reproduce CoTI; calling a sequence “Co-Scientist” does not reproduce its compute, tools, expert process, or validation. Likewise, ASReview's active-learning model and AI Economist's RL agents are different mechanisms from LLM orchestration.

Test routing against the examples above and ambiguous counterexamples. Then evaluate each method against its own success criterion: screening recall, excerpt fidelity, measurement validity, estimator recovery on known synthetic data, prospective forecast scoring, simulation calibration, experiment receipts, held-out engineering tests, proof acceptance, or archival extraction accuracy. Measure wall time and observed token/tool usage separately. No architecture ranking is established by this research pass.

## Coverage, limitations, and confidence

All three framing questions were answered at the architecture-assessment level. Psychology, economics, engineering, biomedicine, mathematics, and history were covered. The pass found more credible evidence for bounded retrieval, executable evaluation, and experimental loops than for universally superior multi-agent teams.

Method recommendations are supported by original studies, official method guidance, and explicit inference. Source families are not fully independent: Co-Scientist, AlphaEvolve, and AlphaProof share Google lineage. CoTI, CausalAgent, and Chronos have narrow evaluation scopes; some findings are from preprints. Publication labels do not substitute for replication.

OpenScholar was discovered but its full article could not be retrieved, so its search snippets do not support a load-bearing conclusion here. This pass does not establish exhaustive coverage, current best-in-class systems, comparative cost efficiency, or local plugin performance. Overall confidence: high that method-specific evidence contracts are needed; moderate in the proposed grouping and adoption order; variable in each architecture's generalizability.
