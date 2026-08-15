#!/usr/bin/env python3
"""Static contract checks for host-neutral Research connector routing."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, *phrases: str) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [phrase for phrase in phrases if phrase not in text]
    if missing:
        raise AssertionError(f"{path} is missing connector policy: {missing}")


def main() -> None:
    require(
        "skills/research/SKILL.md",
        "coding agent's local file, shell, and repository tools",
        "on-device in-app Browser",
        "structured web search/open connector (`web__run`)",
        "smallest valid request",
        "Never construct or evaluate a hand-written wrapper",
    )
    require(
        "commands/research.md",
        "local coding tools first",
        "on-device Browser",
        "structured `web__run` search/open connector as backup",
        "never build an ad-hoc connector wrapper",
    )
    require(
        "AGENTS.md",
        "local coding tools first",
        "on-device in-app Browser",
        "structured `web__run` search/open connector as backup",
        "Don't construct ad-hoc wrappers around connector calls",
    )
    print("connector policy check: PASS")


if __name__ == "__main__":
    main()
