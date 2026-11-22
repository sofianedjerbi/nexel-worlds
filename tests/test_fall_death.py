"""Dying of a fall in your own step (sim/core.py interrupt, entities.py Action.finish)."""

from helpers import run
from test_relief import plateau


def test_a_fall_that_kills_you_in_your_own_step_kills_you(world):
    """gatsu0, 2026-11-22: a fall in a walk took its last hearts and it went on with -4 hp, then -13: the death
    closed the walk from inside itself ("generator already executing") and stopped half way. Now you die whole."""
    sim, a = world
    x, y = a.x, a.y
    plateau(sim, a, h=9)
    a.x, a.y, a.z, a.hp = x, y - 2, 9, 2
    deaths = a.deaths
    r = run(sim, a, "walk", {"dir": "S"})
    assert a.deaths == deaths + 1 and a.hp > 0 and r.get("error") != "bug", (r, a.hp)
