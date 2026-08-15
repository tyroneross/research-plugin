# Capability audit JSON contract

Pass one UTF-8 JSON object to `scripts/render_dashboard.py`. The script validates
this contract before it writes HTML and rejects undeclared fields rather than
silently discarding them. The machine-readable companion is
`../data/audit.schema.json`; the Python validator is authoritative.

## Top-level fields

| Field | Type | Rules |
|---|---|---|
| `title` | string | Non-empty dashboard title. |
| `subtitle` | string | Non-empty scope sentence. |
| `generatedAt` | string | ISO 8601 date or date-time. Do not invent missing time precision. |
| `source` | object | Non-empty `label` and `path`. |
| `scale` | object | Fixed `min: 0`, `max: 3`, and a text `labels` entry for every score. |
| `dimensions` | array | At least one unique `id`; each item has `label`, `short`, and `question`. |
| `subjects` | array | At least one unique `id`; every subject must score every dimension. |
| `overlaps` | array | May be empty; each implementation references a declared subject ID. |
| `gaps` | array | May be empty; each item has `title` and `detail`. |
| `findings` | array | May be empty; each item references a declared subject ID. |
| `recommendation` | object | Bottom line, spine, at least one layer, and at least one next action. |
| `confidence` | object | `context`, `verification`, `evidence`, `overall`, and `note`. |

## Subject fields

Each subject contains:

- `id`, `name`, `oneLiner`, and `role`: non-empty strings.
- `kind`: `plugin`, `app`, `library`, or `platform`.
- `health`: `state` (`ok`, `warn`, or `bad`) plus non-empty `summary`,
  `lastCommit`, and `tests` strings.
- `scores`: an object keyed by every declared dimension ID. Each score contains
  an integer `score` inside the scale, non-empty `evidence` and `cite`, and
  `mark` (`verified`, `inferred`, or `unknown`).
- `strengths` and `gaps`: arrays of strings; empty arrays are allowed.
- `reuse`: objects with non-empty `path` and `what`; an empty array is allowed.

## Findings and recommendation enums

- Finding `severity`: `high`, `normal`, or `low`.
- Finding `state`: `fixed`, `waived`, `escalated`, or `open`.
- Recommendation layer: non-empty `name`, at least one donor string, and a
  non-empty `new` string. Use `No net-new build.` when the source explicitly
  recommends reuse without a new component.

## Annotated minimal example

This is valid JSON. The notes below explain the load-bearing fields.

```json
{
  "title": "Two-tool collection audit",
  "subtitle": "Two tools compared on one collection dimension.",
  "generatedAt": "2026-08-15",
  "source": {"label": "Assessor report", "path": "reports/audit.md"},
  "scale": {
    "min": 0,
    "max": 3,
    "labels": {
      "0": "absent",
      "1": "stub / partial / prompt-only",
      "2": "working but narrow",
      "3": "mature or central"
    }
  },
  "dimensions": [
    {
      "id": "D1",
      "label": "Data collection",
      "short": "Collect",
      "question": "Which sources and formats can it ingest?"
    }
  ],
  "subjects": [
    {
      "id": "tool-a",
      "name": "Tool A",
      "oneLiner": "A focused local-file collector.",
      "kind": "library",
      "health": {
        "state": "ok",
        "summary": "Runs locally.",
        "lastCommit": "2026-08-01",
        "tests": "12/12 pass"
      },
      "scores": {
        "D1": {
          "score": 2,
          "evidence": "Parses PDF and CSV on demand.",
          "cite": "src/collect.py:20",
          "mark": "verified"
        }
      },
      "strengths": ["Simple parser boundary."],
      "gaps": ["No scheduler."],
      "reuse": [{"path": "src/collect.py", "what": "File parser front door."}],
      "role": "Collection donor."
    }
  ],
  "overlaps": [],
  "gaps": [{"title": "Scheduling", "detail": "No subject schedules collection."}],
  "findings": [],
  "recommendation": {
    "bottomLine": "Reuse Tool A for local collection.",
    "spine": "Tool A",
    "layers": [
      {"name": "Collect", "donors": ["Tool A"], "new": "Add a scheduler."}
    ],
    "nextActions": ["Define the scheduler boundary."]
  },
  "confidence": {
    "context": "high",
    "verification": "medium",
    "evidence": "high",
    "overall": "medium",
    "note": "Runtime tests were not executed."
  }
}
```

Key annotations:

1. `generatedAt` preserves source precision: a date stays a date.
2. `scores.D1` exists because every subject must cover every dimension.
3. `mark` states how the evidence was established; it does not change the score.
4. Empty overlap and finding arrays are valid and render as empty sections.
5. Subject references in overlaps and findings use `id`, not display `name`.
