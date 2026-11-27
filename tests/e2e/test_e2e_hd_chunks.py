"""The HD look's land is put together from chunks (vox_style_land.js steps): the ones the store still has, kept, and the
ones made again. A tile touched while a land is being made deletes its chunks from the store; the chunk kept from it
was read from the store again only at the end, frames later, gone: the land was shown with a hole, the ground under
you dark, till the next land made it again (#106)."""

import pytest

from test_e2e_hd_sun import hd, settled

pytestmark = pytest.mark.e2e

# the px 30 px east of your feet, where nothing stands: the ground there, [r, g, b]
GROUND = """(() => { const p = myPos(), a = HdLook.screenOf(p.x + .5, p.y + .92, topAt(p.x, p.y)), k = devicePixelRatio;
  return [...HdLook.read(Math.round((a[0] + 30) * k), Math.round(a[1] * k), 1, 1).data.slice(0, 3)]; })()"""
# the land being made, held, stepped by the test past its scan and its first chunk made again: [its part, the steps]
PAST_SCAN = """(() => { let n = 0; while (!(HdLook.part > 0 && HdLook.part < 1) && HdLook.step()) n++; return [HdLook.part, n]; })()"""
# ...and on to its end, in one call
TO_END = """(() => { let n = 0; while (HdLook.step()) n++; return n; })()"""


# what takes the kept chunks out of the store while the land is made: the tile under you touched (a rock laid near you), or
# the whole land forgotten (eng.lost: the paints ran out; they are wiped only at the next land's start)
MID = {"touch": "(() => { const p = myPos(); HdLook.touch(p.x, p.y); })()", "forget": "HdLook.forget()"}


@pytest.mark.parametrize("mid", sorted(MID))
def test_a_chunk_kept_and_lost_from_the_store_while_the_land_is_made_is_in_that_land(browser, server, mid):
    """The land is held (HdLook.hold = 0) and a tile 14 east of you touched: a land is made with that chunk made again
    and yours kept from the store. Stepped past its scan, the tile under you is touched (its chunk out of the store, as
    a rock laid near you deletes it) or the land forgotten (every chunk out of it), then it is stepped to its end and
    shown: the ground east of your feet is the same px as before. All of it by the making's steps, no frame between
    them: the same at 16 ms a frame as at 200."""
    g = hd(browser, server)
    try:
        settled(g)
        before = g.js(GROUND)
        g.js("HdLook.hold = 0")                              # (the next land is made only as the test steps it)
        g.js("(() => { const p = myPos(); HdLook.touch(p.x + 14, p.y); })()")
        g.wait("HdLook.busy")
        part, steps = g.js(PAST_SCAN)
        assert 0 < part < 1, f"the land had no chunk made again after {steps} steps (part {part})"
        g.js(MID[mid])
        g.js(TO_END)
        g.frames(3)                                          # (the land made shown; the next one, for what was done mid-way, held)
        assert g.js("HdLook.busy"), "the next land went on while held"
        after = g.js(GROUND)
        assert sum(abs(a - b) for a, b in zip(after, before)) < 12, f"the ground east of you went {before} -> {after}"
    finally:
        g.js("HdLook.hold = null")
        g.page.close()
