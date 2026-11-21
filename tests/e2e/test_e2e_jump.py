"""The jump ("player size should be 2 blocks, so 2 blocks to destroy needed; also add a key to jump"): walking into a
step stops you, the jump key (J) hops you up it, on a phone its button; the way out of the ground shows it on a step."""

import pytest
from test_e2e_touch import touch_game

pytestmark = pytest.mark.e2e


def step_east(game):
    """The meadow, a terrace a layer up from two tiles east of you."""
    game.clear_area(6)
    game.stamp(2, -2, ["." * 10] * 5, levels=["1" * 10] * 5)


@pytest.mark.quick
def test_walking_into_a_step_stops_you_and_the_jump_key_climbs_it(game):
    step_east(game)
    x, y = game.pos()
    game.hold(["d"], 700)                                     # three tiles' worth of walking east
    game.rest()
    assert game.pos() == (x + 1, y) and game.server()["x"] == x + 1 and game.server()["z"] == 0     # stopped at the step
    game.frames(2)
    assert "Jump" in game.actions() and "J" in game.js("$('actions').innerText")   # the corner: J Jump
    game.page.keyboard.down("d")                             # walking into it, J: up it, and on
    game.press("j", 0)
    game.sleep(300)
    game.page.keyboard.up("d")
    game.rest()
    s = game.server()
    assert s["x"] >= x + 2 and s["z"] == 1 and game.pos()[0] == s["x"], (s["x"], s["z"], game.pos())
    game.rpc("dev_teleport", x=x + 1, y=y, z=0)              # standing, facing it: J alone
    game.arrive()
    game.face(1, 0)
    game.press("j", 0)
    game.wait(f"meObs.self.x === {x + 2} && meObs.self.z === 1", 4000)
    game.rpc("dev_teleport", x=x - 2, y=y, z=0)              # on the level: a hop where you stand, nothing more
    game.arrive()
    game.press("j", 0)
    hop = game.js("(() => { const p = ents.get('agent' + myId); return [performance.now() - p.hop < 400, myPos().x]; })()")
    assert hop == [True, x - 2]
    assert not game.errors, game.errors


def test_on_a_phone_the_jump_button_shows_at_a_step_and_climbs_it(browser, server):
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        step_east(g)
        x, y = g.pos()
        assert g.js("$('tJump').style.display") == "none"                   # nothing to jump onto
        g.rpc("dev_teleport", x=x + 1, y=y, z=0)
        g.arrive()
        g.face(1, 0)
        g.wait("$('tJump').style.display === 'flex'", 3000)
        r = g.js("(() => { const r = $('tJump').getBoundingClientRect(), a = $('tA').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2, r.bottom <= a.top, r.right <= 390]; })()")
        assert r[2] and r[3], r                                              # over the buttons, on the screen
        g.touch("touchStart", r[0], r[1])
        g.touch("touchEnd")
        g.wait(f"meObs.self.x === {x + 2} && meObs.self.z === 1", 4000)
        assert not g.errors, g.errors
    finally:
        ctx.close()


def test_the_way_out_shows_the_jump_key_on_its_step(game):
    """A tunnel two cells high under a hill, its east end a step up to the open land: the way out's next move is that
    step, and its key is the jump's (the corner, and the cap beside the step), not nothing."""
    game.clear_area(14)
    x, y = game.pos()
    game.stamp(-1, -1, ["." * 12] * 3, levels=["6666" + "1" * 8, "6000" + "1" * 8, "6666" + "1" * 8],
               roofs=["0" * 12, "0666" + "0" * 8, "0" * 12])
    game.rpc("dev_teleport", x=x + 2, y=y, z=0)
    game.arrive()
    game.rest()
    game.wait("WayShow.cur && !WayShow.busy && WayShow.offer() && WayShow.offer().key === 'jump'", 8000)
    game.frames(3)
    assert "Jump" in game.js("$('actions').innerText")
    cap = game.js("(() => { const e = document.getElementById('waycap'); return e && e.style.display === 'block' ? e.innerText : ''; })()")
    assert "J" in cap, cap
    game.press("j", 0)
    game.wait(f"meObs.self.x === {x + 3} && meObs.self.z === 1", 4000)
    assert not game.errors, game.errors
