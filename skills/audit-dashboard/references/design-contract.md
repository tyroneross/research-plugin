# Audit dashboard design contract

Use these rules for every rendered capability audit. The dashboard is a static,
evidence-led projection of its source payload; it does not edit the audit.

## Visual system

- Use one dark theme with these exact tokens:
  - page `#0b0e13`
  - primary surface `#12161d`
  - card `#1a1f28`
  - border `#262c37`
  - text `#e8edf3`
  - muted `#9aa7b5`
  - accent `#4da3ff`
  - confirmed `#43c987`
  - review `#e3b341`
  - blocker `#f06a6a`
- Reserve the accent for navigation, links, focus, and column-best emphasis.
- Reserve green, amber, and red for confirmed, review, and blocking states.
- Use the system font stack at `14px/1.5`; use `12px` for metadata.
- Use `10px` radii, `1px` borders, and approximately `16px 18px` card padding.
- Set the body background explicitly. Keep payload values out of CSS.

## Layout and hierarchy

- Render exactly four top-level areas in this order: Overview, Matrix, Subjects,
  Findings.
- Use an approximately `250px` sticky sidebar at widths of `760px` and above.
- Below `760px`, convert navigation to a horizontally scrollable top bar and use
  approximately `14px` horizontal content padding.
- Prevent page-level horizontal overflow. Put wide-table overflow inside the
  table container.
- Keep content at least 70% of the viewport. Prefer hierarchy, spacing, and
  grouping over decorative chrome.
- Group related content under one border with internal spacing or dividers. Do
  not place an individual box around each list item.

## Overview

- Lead with a source-and-date kicker, title, subtitle, and this authority line:
  `Projection of <source>; scores are the auditors' judgment.`
- Show metrics for subject count, dimension count, findings by state, and the
  tied column-best subjects for every dimension.
- Show the bottom line before the recommended spine.
- Show every recommendation layer with its donors and net-new work.
- Keep confidence and next actions adjacent to the recommendation.

## Matrix

- Render one comparison table with a caption, subjects as rows, dimensions as
  columns, and health as the final column.
- Show every score as dots, a numeric value, and the scale's text label.
- Give the score summary an `aria-label` and `title` containing the numeric value
  and scale label.
- Outline every tied column-best cell and add visible `best` text.
- Use native `details`/`summary` disclosure for evidence, cite, and verification
  mark. The evidence remains readable with JavaScript disabled.
- Render marks as `verified` with ✅, `inferred` with ⚠️, and `unknown` with ❓.
- Render health as both a state pill and explicit summary text.

## Subjects

- Render one responsive card per subject.
- Keep name, kind, one-liner, health, last commit, tests, dimension mini-rows,
  strengths, gaps, reuse candidates, and role in the same card.
- Keep each mini-score numeric and textual as well as visual.
- Render empty lists honestly as `None reported.`

## Findings

- Render an overlaps table with capability, implementations, and keep columns.
- Render cross-subject gaps as a plain grouped list.
- Render a findings table with subject, severity, finding, state, and record.
- Pair every severity and state color with its text label.

## Accessibility and integrity

- Use semantic `nav`, `main`, `section`, headings, table captions, row/column
  headers, and a skip-to-content link.
- Provide visible keyboard focus and at least `44px` interactive targets.
- Respect `prefers-reduced-motion` and keep the page useful without JavaScript.
- Never encode a number or state by color alone.
- Escape every payload-derived text and attribute value with HTML quote escaping.
- Do not derive raw DOM identifiers, CSS, or JavaScript from payload strings.
- Include no remote fonts, styles, scripts, images, analytics, or chart libraries.
- Do not add decorative charts for single facts or controls that imply mutation.

## v2 pipeline-first layout

When `stages`, subject pipelines, and recommendation flow are present, render Recommended flow, Pipelines today, Comparison, then Notes. Use native dialog pop-outs for score details with a no-JavaScript details fallback. Group comparison columns by stages, place an Optimal row under each group, and use one left-aligned monospace dot run in every score cell. Visible body copy uses full sentences and excludes file paths; cites appear only in the muted pop-out footer.
