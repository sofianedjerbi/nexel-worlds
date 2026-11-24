"""The far land a page asks for (state.js: a region with `far`, for the HD look's horizon) is made off the server's
tick (views.py far_ready: world.prefetch), never at once: 30 ms a chunk made in the reply stalled the ticks."""

import time

from nexel_worlds.server import GameServer


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


def test_far_land_is_given_only_near_what_the_page_watches(tmp_path):
    """The farthest view distance asks for land some 110 tiles out (hd.js viewOf); a page is never given far land past
    FAR_VIEW tiles of the rectangle it watches, nor before it has said what it watches: it cannot have the world made."""
    from nexel_worlds.views import FAR_VIEW
    gs = GameServer(tmp_path / "w", seed=3)
    watch = (100, 100, 60, 40)                                # its screen and what its HD look shows
    assert gs.far_near(watch, 100 + 60 + FAR_VIEW - 32, 100, 32, 32)          # a block 128 tiles east of it: yes
    assert gs.far_near(watch, 100 - FAR_VIEW - 32, 100 - FAR_VIEW - 32, 32, 32)
    assert not gs.far_near(watch, 100 + 60 + FAR_VIEW + 1, 100, 32, 32)       # past it: no
    assert not gs.far_near(watch, 5000, -5000, 32, 32)
    assert not gs.far_near(None, 100, 100, 32, 32)            # nothing watched yet
    assert not gs.far_near(watch, 100, 100, 256, 256)         # far land a block at a time
