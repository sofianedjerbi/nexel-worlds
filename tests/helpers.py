"""Shared helpers for the simulation tests."""

from megastructure.sim import Simulation


def make(tmp_path, name="w"):
    return Simulation(tmp_path / f"{name}.sqlite", seed=7)


def clear(sim, a, r=6):
    """Flat empty deck around the agent (flat in height too, out to 3r), and no creatures, for predictable tests."""
    for y in range(a.y - 3 * r, a.y + 3 * r + 1):
        for x in range(a.x - 3 * r, a.x + 3 * r + 1):
            sim.world.set(x, y, level=0)
    for y in range(a.y - r, a.y + r + 1):
        for x in range(a.x - r, a.x + r + 1):
            sim.world.set(x, y, ground="dirt", block="none", level=0)
    sim.creatures.clear()


def run(sim, a, tool, args=None, limit=500):
    act = sim.submit(a, tool, args or {})
    for _ in range(limit):
        if act.result is not None:
            return act.result
        sim.step()
    raise AssertionError(f"{tool} did not finish")


def sim_ripen_ticks():
    """Ticks for a sprout to become a ripe crop (two 150 s stages), with a little slack."""
    from megastructure.sim import sec
    return 2 * sec(150) + sec(4)
