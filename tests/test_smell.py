"""The code-health counts (tools/smell.py) only go down: one that grows past tools/smell.json fails here.

Lowered one? Run `uv run python tools/smell.py --write` so the new count is the one held.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import smell  # noqa: E402

HELD = json.loads(smell.BASELINE.read_text())
NOW = smell.counts()


def test_every_count_is_held():
    assert set(NOW) == set(HELD), "tools/smell.json and tools/smell.py count different things: run tools/smell.py --write"


@pytest.mark.parametrize("name", sorted(HELD))
def test_the_count_does_not_grow(name):
    assert NOW[name] <= HELD[name], (f"{name} went up from {HELD[name]} to {NOW[name]} (tools/smell.py says what it counts "
                                     "and where): say what the code does now, name the number, or ask the owner of the rule")


def test_the_counts_see_what_they_are_for():
    assert smell.PATCH.search("// (it was drawn twice)") and not smell.PATCH.search("// (drawn once, at the feet)")
    assert smell.SIXTEEN.findall("x * 16 + 16.5, P16, a16") == ["16"]
    assert smell.special(["if (onLadder(p) && wet(x)) go();"]) == {"ladder": 1, "water": 1}
