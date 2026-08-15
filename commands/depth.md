---
description: Classify a research request as light, standard, or deep before sourcing
argument-hint: <topic-or-question> [--json]
allowed-tools: Bash
---

Classify the requested research depth before choosing the workflow.

```bash
python3 "${RESEARCH_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT}}}/research.py" depth $ARGUMENTS
```

Use the result to decide scope:

- `light` — quick answer, usually 0-2 sources, skip persistence unless the answer is reusable.
- `standard` — bounded research, usually 3-8 sources with a target of 5, persist when the result is more than a short answer.
- `deep` — decision-grade or explicitly thorough/expansive research, usually 7-15 sources with a target of 10, include verification and persist by default.

If the classifier and user language conflict, the user's explicit depth request wins.
Use the printed coverage lanes to plan primary/original sources, independent corroboration, counter-evidence, currentness checks, and explicit gaps before fetching.
