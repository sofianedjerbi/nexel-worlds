"""Dev tools (QA builds): they never leave the players stuck."""

from helpers import run
from nexel_worlds.devtools import dev_op
from nexel_worlds.sim import DAY_TICKS


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

    from nexel_worlds import views
    from nexel_worlds.server import GameServer
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


def test_the_worlds_clock_is_paced_only_by_the_dev_tool_and_the_server_ticks_by_it(world, tmp_path):
    """dev_pace (the browser tests' clock, tests/e2e/clock.py): the server makes that many times its ticks a second;
    a world nobody paced ticks ten times a second, as ever."""
    import asyncio

    from nexel_worlds.server import GameServer
    from nexel_worlds.sim import TICK_HZ

    sim, a = world
    assert not hasattr(sim, "clock_rate")                    # (not there until asked for: the server reads 1)
    assert dev_op(sim, a, "dev_pace", {"pace": 4}) == {"pace": 4.0}
    assert dev_op(sim, a, "dev_pace", {"pace": 1000})["pace"] == 16 and dev_op(sim, a, "dev_pace", {"pace": 0})["pace"] == .05

    def ticks(pace, secs=.6):
        gs = GameServer(tmp_path / f"w{pace}", seed=3)
        if pace:
            dev_op(gs.sim, None, "dev_pace", {"pace": pace})

        async def play():
            loop, t0 = asyncio.create_task(gs.tick_loop()), gs.sim.tick
            await asyncio.sleep(secs)
            gs.stopping.set()
            await loop
            return gs.sim.tick - t0
        n = asyncio.run(play())
        gs.sim.close()
        return n / secs / TICK_HZ

    assert .7 < ticks(None) < 1.3 and 3 < ticks(4) < 5


def test_in_lockstep_the_world_ticks_when_its_driver_asks_and_never_stays_frozen(tmp_path):
    """dev_lockstep and dev_step (#276, the browser tests' one clock): a socket driving the ticks gets the world at the
    tick it asks for, once (absolute: asked again, nothing more is made), and none in between; another socket is not
    the driver; let go, or its socket gone, the world is on the wall's clock again."""
    import asyncio

    from nexel_worlds.server import GameServer

    gs = GameServer(tmp_path / "w", seed=3, dev=True)
    page, other = object(), object()

    async def play():
        loop = asyncio.create_task(gs.tick_loop())
        await asyncio.sleep(.15)
        t0 = gs.lockstep(page, {"on": True})["tick"]
        await asyncio.sleep(.4)
        held = gs.sim.tick - t0                               # (4 ticks of the wall's: none in lockstep)
        to = (await gs.step(page, {"to": t0 + 3}))["tick"]
        again = (await gs.step(page, {"to": t0 + 3}))["tick"]
        await asyncio.sleep(.2)
        still = gs.sim.tick
        refused = await gs.step(other, {"to": t0 + 9})
        far = (await gs.step(page, {"to": t0 + 10 ** 6}))["tick"]   # (100 ticks on at the most)
        gs.lockstep(page, {"on": False})
        t1 = gs.sim.tick
        await asyncio.sleep(.4)
        gs.stopping.set()
        await loop
        return held, to, again, still, refused, far, gs.sim.tick - t1
    held, to, again, still, refused, far, freed = asyncio.run(play())
    gs.sim.close()
    t0 = to - 3
    assert held == 0 and to == again == still == t0 + 3, (held, to, again, still)
    assert refused["ok"] is False and refused["error"] == "not_driver" and far == still + 100
    assert freed >= 2                                         # (back on the wall's clock: 10 a second)


def test_in_lockstep_a_screen_with_no_view_yet_hears_every_tick(tmp_path):
    """A page in lockstep runs its next frame once its tick has come, and tells the world what it watches from a timer of
    its frames: a screen with no view yet (just woken, the island's view dropped) heard no tick, made no frame, never told
    it, and the world waited for it (#303's hung run). In lockstep it hears every tick, nothing in it; off, as before."""
    import asyncio
    import json

    from nexel_worlds.server import GameServer

    gs = GameServer(tmp_path / "w", seed=3, dev=True)
    q = asyncio.Queue()
    gs.spectators[q] = None
    gs.push_ticks()
    off = q.qsize()
    gs.lockstep(object(), {"on": True})
    gs.push_ticks()
    d = json.loads(q.get_nowait())
    gs.sim.close()
    assert off == 0 and d["type"] == "tick" and d["tick"] == gs.sim.tick and d["entities"] == [] and d["items"] == []


def test_in_lockstep_a_world_sent_on_by_a_dev_op_tells_its_screens_its_tick(tmp_path):
    """dev_time and dev_skip move the world's tick outside its loop: no tick of theirs was sent, so a page in lockstep
    (clock.py STEP), waiting for the tick it asked for to come, waited for ever when the world was already there
    (#303's hung run: dev_time at every test's join). In lockstep the tick they leave is sent to the screens."""
    import asyncio
    import json

    from nexel_worlds.server import GameServer

    gs = GameServer(tmp_path / "w", seed=3, dev=True)
    screen = asyncio.Queue()
    gs.spectators[screen] = (0, 0, 10, 10)

    class Ws:
        request = type("R", (), {"path": "/agent", "headers": {}})()
        remote_address = ("127.0.0.1", 0)

        async def send(self, m):
            pass

        async def close(self, *a):
            pass

        def __aiter__(self):
            async def it():
                for i, m in enumerate(({"op": "hello", "name": "Pip", "token": "t"}, {"op": "dev_lockstep", "on": True},
                                       {"op": "dev_skip", "seconds": 0.1})):
                    yield json.dumps({"id": i, **m})
                    await asyncio.sleep(0)
            return it()

    asyncio.run(gs.agent_session(Ws()))
    ticks = [json.loads(m)["tick"] for m in iter(lambda: screen.get_nowait() if not screen.empty() else None, None)
             if json.loads(m).get("type") == "tick"]
    gs.sim.close()
    assert ticks and ticks[-1] == gs.sim.tick, (ticks, gs.sim.tick)


def test_a_seeded_worlds_chances_are_the_same_at_every_run(world):
    """dev_seed (#276): the world's chances (sim.rng) from a test's own seed: the same seed, the same draws."""
    sim, a = world
    assert dev_op(sim, a, "dev_seed", {"seed": 12345}) == {"seed": 12345}
    one = [sim.rng.random() for _ in range(5)]
    dev_op(sim, a, "dev_seed", {"seed": 12345})
    assert [sim.rng.random() for _ in range(5)] == one
    dev_op(sim, a, "dev_seed", {"seed": 54321})
    assert [sim.rng.random() for _ in range(5)] != one
