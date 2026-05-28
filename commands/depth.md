---
description: Classify a research request as light, standard, or deep before sourcing
argument-hint: <topic-or-question> [--json]
allowed-tools: Bash
---

Classify the requested research depth before choosing the workflow.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/research.py" depth $ARGUMENTS
```

Use the result to decide scope:

- `light` — quick answer, usually 0-2 sources, skip persistence unless the answer is reusable.
- `standard` — bounded research, usually 2-5 sources, persist when the result is more than a short answer.
- `deep` — decision-grade research, usually 4-10 sources, include verification and persist by default.

If the classifier and user language conflict, the user's explicit depth request wins.
