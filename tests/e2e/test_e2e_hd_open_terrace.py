"""On a stepped stone hill under the open sky (#70): the land's x-ray cut never opens. The owner stood on the terraces of
a stone hill, nothing over his head: the cut opened and the terraces round and under him were grey see-through stone, the
prompt "Dig into the hill", as if the land hid him. The window opens only when land covers or hides you."""

import pytest
from test_e2e_hd_sun import hd

# terraces from the north down to the south: 9, 8, 7 (you), 6, 5. Hills of 5 and up are stone at every height (stone.py)
TERRACES = ["9"] * 2 + ["8"] * 2 + ["7"] * 4 + ["6"] * 2 + ["5"] * 3
STATE = "({win: HdLook.win.n, open: HdLook.win.a, hid: HdLook.hid, roof: HdLevel.cover.roof, level: HdLook.level[0], z: myAt && myAt.z})"


# the same terraces climbing to the SOUTH: the land between the eye and you rises (HdLevel.hides)
UP_SOUTH = list(reversed(TERRACES))


@pytest.mark.parametrize("rows, dx", [(TERRACES, 0), (TERRACES, 3), (UP_SOUTH, 0)], ids=["down_south", "down_south_east", "up_south"])
def test_on_an_open_stone_terrace_the_land_is_not_cut(browser, server, rows, dx):
    g = hd(browser, server)
    try:
        g.stamp(-7, -6, ["." * 15] * len(rows), levels=[r * 15 for r in rows])
        g.rest()
        x, y = g.pos()
        g.rpc("dev_teleport", x=x + dx, y=y, z=7)
        g.arrive()
        g.rest()
        g.frames(10)
        s = g.js(STATE)
        assert s["z"] == 7 and not s["roof"] and not s["hid"] and not s["win"] and not s["open"], s
        assert not g.errors
    finally:
        g.page.close()


@pytest.fixture(scope="module")
def seed12(tmp_path_factory):
    """The owner's world as the generator makes it (saves/caves is seed 12): where #70 was seen."""
    import socket
    import subprocess
    import sys
    import time

    from conftest import ROOT, free_port
    port, saves = free_port(), tmp_path_factory.mktemp("seed12")
    proc = subprocess.Popen([sys.executable, "-m", "nexel_worlds.server", "--saves", str(saves), "--world", "e2e12",
                             "--port", str(port), "--seed", "12", "--dev"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=.2).close()
            break
        except OSError:
            time.sleep(.1)
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    proc.wait(10)


WHY = """(() => { const t = myPos(), L = myAt && myAt.z; return {pos: t, L, top: topAt(t.x, t.y), col: Voxels.host.column(t.x, t.y),
  south: [1, 2, 3].map((d) => topAt(t.x, t.y + d)), over: HdLevel.over(t.x, t.y, L, eyeRise(HdLook.cam.pitch)), pitch: HdLook.cam.pitch}; })()"""


def test_where_the_owner_stood_the_land_is_not_cut(browser, seed12):
    """#70 as it was seen: seed 12, (13, -72) at level 5, grass terraces up to the north, stone ones down to the south."""
    g = hd(browser, seed12)
    try:
        g.rpc("dev_teleport", x=13, y=-72, z=5)
        g.arrive()
        g.rest()
        g.frames(10)
        s = g.js(STATE)
        assert not s["roof"] and not s["hid"] and not s["win"] and not s["open"], (s, g.js(WHY))
    finally:
        g.page.close()


def test_walking_up_the_owners_hill_the_cut_shuts_where_you_show(browser, seed12):
    """#70 as it came: walking south up the terraces to where the owner stood. A terrace two tiles on, two levels over you,
    hides you whole (y -75: 9 % of you shows with no cut): the cut opens there, rightly. Where the owner stopped (y -72) a
    step a level up covers your legs, half of you shows: the cut is shut. (It stayed open: the hole's lower bar, PART.)"""
    g = hd(browser, seed12)
    try:
        g.rpc("dev_teleport", x=13, y=-76, z=3)
        g.arrive()
        g.rest()
        g.page.keyboard.down("ArrowDown")
        try:
            g.wait("myPos().y >= -72", timeout=15000)
        finally:
            g.page.keyboard.up("ArrowDown")
        g.wait("!walking && [-72, -71].includes(myPos().y)", timeout=6000)      # (let go at -72, the step under way ends there or on -71: half of you or more shows on both)
        g.wait("!HdLook.hid && !HdLook.win.a", timeout=4000)                 # (the window's hold, 300 ms, then shut)
        s = g.js(STATE)
        assert s["z"] in (5, 6) and not s["hid"] and not s["win"] and not s["open"], (s, g.js(WHY))
    finally:
        g.page.close()
