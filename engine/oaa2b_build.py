#!/usr/bin/env python3
"""Keep the vault a tree, then regenerate every generated file (hubs, home, INDEX, WARNINGS, START-HERE, graph colours), in place.

    oaa2b_build.py <vault-dir>

Writes a file only when its content changes, so an unchanged vault produces no churn.
Running it twice in a row must change nothing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oaa2b_tree  # noqa: E402
import oaa2b_vault as vt  # noqa: E402


def build(vault):
    vault = Path(vault).resolve()
    vt.write_graph(vault)  # first, so its folder already exists when the hubs are listed
    oaa2b_tree.enforce(vault)
    made = vt.load_warnings(vault)
    vt.generate(vault, made)
    vt.start_here(vault, made)


if __name__ == "__main__":
    build(sys.argv[1])
