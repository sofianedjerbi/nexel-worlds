"""The far land a page asks for (state.js: a region with `far`, for the HD look's horizon) is made off the server's
tick (views.py far_ready: world.prefetch), never at once: 30 ms a chunk made in the reply stalled the ticks."""

import time

from megastructure.server import GameServer


def test_far_land_not_made_yet_is_made_off_the_tick_then_given(tmp_path):
    gs = GameServer(tmp_path / "w", seed=3)
    world = gs.sim.world
    x, y = 32 * 40, 32 * -40                                  # far from anything made
    assert (40, -40) not in world.chunks and not world.store.has_chunk(40, -40)
    assert not gs.far_ready(x, y, 32, 32)                    # asked for: made on a thread, not in the reply
    assert (40, -40) not in world.chunks and (40, -40) in world._pending
    for _ in range(200):                                      # (a few ticks on, and the thread done)
        gs.sim.step()
        if gs.far_ready(x, y, 32, 32):
            break
        time.sleep(.01)
    assert (40, -40) in world.chunks
    out = gs.region(x, y, 32, 32)
    assert len(out["rows"]) == 32 and len(out["levels"]) == 32
    assert gs.far_ready(32 * 0, 32 * 0, 32, 32) or (0, 0) in world._pending   # (near land: the same way)
