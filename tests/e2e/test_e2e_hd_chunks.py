"""The HD look's land is put together from chunks (vox_style_land.js steps): the ones the store still has, kept, and the
ones made again. A tile touched while a land is being made deletes its chunks from the store; the chunk kept from it
was read from the store again only at the end, frames later, gone: the land was shown with a hole, the ground under
you dark, till the next land made it again (#106)."""

import pytest

from test_e2e_hd import PUT, ROOF
from test_e2e_hd import hd as hd_house
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


# you there, on the server and drawn on that tile (arrive() waits for the land made too: held here, it never is)
ON = "(() => { const p = ents.get('agent' + myId), s = myPos(); return !!p && !!s && s.x === %d && s.y === %d && p.x === %d && p.y === %d; })()"
# the land being made, held, stepped (HdLook.step) till it has asked for the pieces of tile [x, y] (HdThings.at: what is
# built there, its roof cut or not by where you stand): -> the steps taken, -1 if the land was made before it asked
ASK = """([x, y]) => { const a0 = HdThings.at, k = x + ',' + y; let asked = false, n = 0;
  HdThings.at = function (X, Y) { if (X + ',' + Y === k) asked = true; return a0.apply(this, arguments); };
  try { while (!asked) { n++; if (!HdLook.step()) return -1; } return n; } finally { HdThings.at = a0; } }"""


@pytest.mark.stepped
def test_a_chunk_of_land_made_while_you_go_into_a_room_is_made_again(browser, server):
    """(#358) The land is made a tile a step, a chunk over several frames. Its key (hd.js chunkKey: where you are,
    what is built, the doors) was read when the chunk was done: a chunk begun with you on the door, the roof's front
    row whole over it, and done once you were in the room had the room's key, and the next land kept it, the roof row
    across you: 0.6 of you seen (test_a_built_house_has_its_roof_outside_and_is_open_inside, one run in ten). Now the
    key is the one the chunk began with: made over a change, it is made again."""
    g = hd_house(browser, server)
    try:
        x, y = g.pos()
        x0, y0 = x - 1, y - 5
        g.stamp(-1, -5, ["WWWW", "WnnW", "W+WW"])
        g.rpc("dev_give", items={"roof": 12})
        room = [[x0 + 1, y0 + 1, 0], [x0 + 2, y0 + 1, 0]]
        assert g.js(PUT, [[[x0 + i, y0 + j, 3, "roof"] for j in (2, 1, 0) for i in range(4)], room]) == []
        g.rpc("dev_teleport", x=x, y=y, z=0); g.arrive()
        g.wait(f"({ROOF})([{x0 + 1}, {y0 + 1}]) && HdLook.win.a === 0", timeout=8000)
        g.rest()
        g.js("HdLook.hold = 0")                                  # (the next land is made only as the test steps it)
        try:
            g.rpc("dev_teleport", x=x0 + 1, y=y0 + 2, z=0); g.until(ON % (x0 + 1, y0 + 2, x0 + 1, y0 + 2), 600)   # on the door
            steps = g.js(ASK, [x0 + 1, y0 + 2])
            assert steps > 0, steps                              # (a land under way, its chunk with the door row begun, not done)
            g.rpc("dev_teleport", x=x0 + 1, y=y0 + 1, z=0); g.until(ON % (x0 + 1, y0 + 1, x0 + 1, y0 + 1), 600)   # into the room, the land still held
        finally:
            g.js("HdLook.hold = null")
        g.until("!HdLook.busy && HdLevel.place.ty === %d" % (y0 + 1), 2400)
        g.rest()
        seen = g.js("HdLook.catSeen()")
        assert seen > .8, (seen, g.js("([x, y]) => [[x, y], [x, y + 1]].map(([a, b]) => (HdThings.at(a, b) || []).map((q) => [q.z, q.h]))", [x0 + 1, y0 + 1]))
    finally:
        g.page.close()
