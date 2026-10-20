#!/usr/bin/env python3
"""Create an earnings scaffold; implementation and mutations live in research.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research import main

if __name__ == "__main__":
    sys.exit(main(["earnings-init", *sys.argv[1:]]))
