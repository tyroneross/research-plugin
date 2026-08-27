# Bounded second- and third-level traversal

Treat the seed page as depth 0. Traverse breadth-first so one branch cannot consume the budget.

## Required limits

- Default maximum depth: 2.
- Depth 3: explicit evidence-gap reason in the run contract.
- Domain allowlist and denied schemes.
- Maximum pages, bytes, and wall-clock seconds.
- Robots policy: respect rules and fail closed when robots cannot be reached because of server or network errors.
- Private, loopback, link-local, reserved, file, and credential-bearing destinations: deny unless the user explicitly placed them in scope.
- Authentication, connected-app permission, copyright, and terms: evaluate separately from robots.

## Link record

Record every considered link, including rejection:

- parent observation ID and source URL;
- displayed href and resolved URL;
- depth and discovery order;
- accepted or rejected;
- rejection reason;
- fetch/capture result and representation hash;
- evidence gap the page was expected to address.

Prefer links likely to add primary evidence, methods, cited data, correction history, author identity, counter-evidence, or newer versions. Do not follow navigation, login, share, tracking, or repeated calendar/archive links unless they answer a named gap.

Use conditional retrieval for a previously observed URL when the host supports it. Keep server ETag or Last-Modified separate from the local raw-byte hash.
