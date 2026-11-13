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


def test_a_spectator_that_missed_events_is_told_to_ask_for_its_land_again(tmp_path):
    """Every spectator hears every event, but only so many may wait in its queue: thousands of tiles changing at once
    and the rest were dropped, without a word (its picture of that land stayed wrong until its next routine refresh)."""
    import asyncio

    from megastructure import views
    from megastructure.server import GameServer
    gs = GameServer(tmp_path / "w", seed=3)
    q = asyncio.Queue()
    gs.spectators[q] = None
    for i in range(views.QUEUE_MAX + 50):
        gs._broadcast({"type": "tile", "x": i, "y": 0})
    assert q.qsize() == views.QUEUE_MAX and q in gs.behind
    gs.push_ticks()
    assert q in gs.behind                                    # still far behind: not yet
    while q.qsize() > 10:
        q.get_nowait()
    gs.push_ticks()
    rest = [q.get_nowait() for _ in range(q.qsize())]
    assert '{"type":"resync"}' in rest and q not in gs.behind
    gs.sim.close()


def test_clearing_the_ground_for_a_test_takes_what_lies_on_it_too(world):
    """dev_creatures with `clear` (the tests' clear_area) removes the piles near as well as the creatures: a pile one
    browser test left was drawn, and counted, in another's whenever its player woke near it. Without `clear` (a
    creature spawned) nothing on the ground is touched."""
    sim, a = world
    sim.items[(a.x + 2, a.y)] = {"wood": 1}
    sim.items[(a.x + 60, a.y)] = {"stone": 1}
    dev_op(sim, a, "dev_creatures", {"kind": "cow", "dx": 1, "dy": 0})
    assert (a.x + 2, a.y) in sim.items
    dev_op(sim, a, "dev_creatures", {"clear": 40})
    assert (a.x + 2, a.y) not in sim.items and (a.x + 60, a.y) in sim.items and not sim.creatures
