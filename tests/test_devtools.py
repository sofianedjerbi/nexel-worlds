"""Dev tools (QA builds): they never leave the players stuck."""

from helpers import run
from megastructure.devtools import dev_op
from megastructure.sim import DAY_TICKS


def test_setting_the_hour_never_turns_the_clock_back(world):
    """dev_time went back to this morning when the hour asked for was past: everyone's cooldowns were then stamped in
    the future, and nobody could take a step for minutes."""
    sim, a = world
    sim.tick = int(DAY_TICKS * .6)                           # afternoon
    assert run(sim, a, "step", {"dir": "E"})["ok"]
    before = sim.tick
    dev_op(sim, a, "dev_time", {"phase": .3})                # "morning": tomorrow's
    assert sim.tick >= before and sim.tick % DAY_TICKS == int(DAY_TICKS * .3)
    x = a.x
    assert run(sim, a, "step", {"dir": "E"}, limit=5)["ok"] and a.x == x + 1     # ...and you walk on at once
    dev_op(sim, a, "dev_time", {"phase": .8})                # later today: today's
    assert sim.tick // DAY_TICKS == before // DAY_TICKS + 1
