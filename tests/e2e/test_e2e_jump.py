"""The jump ("player size should be 2 blocks, so 2 blocks to destroy needed; also add a key to jump"; then "Jump looks
unnatural. Add automatic jump by default"): walking into a step jumps you up it (auto-jump, a setting); with it off
walking into a step stops you and the jump key (Space) hops you up it, on a phone its button; the way out of the ground
shows it on a step. The jump is a crouch, an arc that clears the step, a landing."""

import pytest
from test_e2e_touch import touch_game

pytestmark = pytest.mark.e2e


def step_east(game):
    """The meadow, a terrace a layer up from two tiles east of you."""
    game.clear_area(6)
    game.stamp(2, -2, ["." * 10] * 5, levels=["1" * 10] * 5)


AUTO = "(v) => { setOpt('autojump', v); return opt('autojump'); }"


@pytest.mark.quick
def test_auto_jump_is_on_by_default_and_walking_into_a_step_jumps_up_it(game):
    """No key: held east, you go up the step and on, never stopping; the world has you where the screen does."""
    step_east(game)
    x, y = game.pos()
    assert game.js("OPT_DEFAULT.autojump === true && opt('autojump') === true")
    assert game.js("MENU_PAGES.find((pg) => pg[0] === 'Keys')[1].filter((r) => r.name === 'Auto-jump' && r.kind === 'toggle').length") == 1   # (a setting on the Keys page)
    game.start_recording()
    game.hold(["d"], 700)                                     # three tiles' worth of walking east: up the step at x + 2
    rec = game.recording()
    game.rest()
    s = game.server()
    assert s["x"] >= x + 3 and s["z"] == 1 and game.pos()[0] == s["x"], (s["x"], s["z"], game.pos())
    xs = [r[1] for r in rec if r[1] < x + 2.5]                # (up to past the step: never back, never a stop)
    assert all(b >= a - 1e-6 for a, b in zip(xs, xs[1:])), xs
    assert not game.errors, game.errors


@pytest.mark.quick
def test_walking_into_a_step_stops_you_and_the_jump_key_climbs_it(game):
    """Auto-jump off (the settings' Keys page): the step stops you and Space climbs it."""
    step_east(game)
    x, y = game.pos()
    assert game.js(AUTO, False) is False
    try:
        walk_into_a_step_then_jump(game, x, y)
    finally:
        game.js(AUTO, True)


def walk_into_a_step_then_jump(game, x, y):
    game.hold(["d"], 700)                                     # three tiles' worth of walking east
    game.rest()
    assert game.pos() == (x + 1, y) and game.server()["x"] == x + 1 and game.server()["z"] == 0     # stopped at the step
    game.frames(2)
    assert "Jump" in game.actions() and "Space" in game.js("$('actions').innerText")   # the corner: Space Jump
    game.page.keyboard.down("d")                             # walking into it, Space: up it, and on
    game.press("Space", 0)
    game.sleep(300)
    game.page.keyboard.up("d")
    game.rest()
    s = game.server()
    assert s["x"] >= x + 2 and s["z"] == 1 and game.pos()[0] == s["x"], (s["x"], s["z"], game.pos())
    game.rpc("dev_teleport", x=x + 1, y=y, z=0)              # standing, facing it: Space alone
    game.arrive()
    game.face(1, 0)
    game.press("Space", 0)
    game.wait(f"meObs.self.x === {x + 2} && meObs.self.z === 1", 4000)
    game.rpc("dev_teleport", x=x - 2, y=y, z=0)              # on the level: a hop where you stand, nothing more
    game.arrive()
    game.press("Space", 0)
    hop = game.js("(() => { const p = ents.get('agent' + myId); return [performance.now() - p.hop < 400, myPos().x]; })()")
    assert hop == [True, x - 2]
    assert not game.errors, game.errors


ARC = """() => { window.__arc = []; window.__arcOn = true; const f = () => { const p = ents.get('agent' + myId), j = p && jumpOf(p);
  if (j) __arc.push([+p.x.toFixed(3), +j.body.toFixed(2), j.squash, j.pose]); if (__arcOn) requestAnimationFrame(f); }; requestAnimationFrame(f); return 1; }"""


@pytest.mark.realtime
def test_the_jump_is_a_crouch_an_arc_over_the_step_and_a_landing(game):
    """Frame by frame up a step, walking: squashed on the ground first, then the height over the floor it left rises
    and falls, its top over the step's (a block: 16 art px), squashed on landing. (It left the ground at once, stiff.)"""
    step_east(game)
    x, y = game.pos()
    game.js(ARC)
    game.hold(["d"], 600)
    rec = game.js("(() => { __arcOn = false; return __arc; })()")
    game.rest()
    assert game.server()["z"] == 1
    up = [(px, body + 16 * (px - (x + 1)), sq) for px, body, sq, _ in rec if x + 1 < px < x + 2]   # height over the floor it left, per frame
    air = [h for _, h, sq in up if not sq]
    assert len(air) >= 3 and any(sq for _, _, sq in up), up                    # (in the air, and squashed on the ground: a crouch or a landing)
    top = air.index(max(air))
    assert max(air) > 16 and 0 < top < len(air) - 1, air                      # its top clears the step
    assert all(b >= a for a, b in zip(air[:top], air[1:top + 1])) and all(b <= a for a, b in zip(air[top:], air[top + 1:])), air
    poses = [pose for px, _, _, pose in rec if x + 1 < px < x + 2]
    seen = [a for a, b in zip(poses, [None] + poses) if a != b]               # each pose once, in the order shown
    order = ["crouch", "takeoff", "rise", "apex", "fall", "land", "settle"]
    assert seen[0] == "crouch" and seen[-1] in ("land", "settle") and "takeoff" in seen and "apex" in seen, seen
    assert [order.index(a) for a in seen] == sorted(order.index(a) for a in seen), seen      # (never back to a pose it has left)
    assert not game.errors, game.errors


POSES = """() => { const c = document.createElement('canvas'); c.width = 384; c.height = 192; const g = c.getContext('2d', {willReadFrequently: true});
  g.drawImage(IMG.character, 0, ANIM.jump * 48, 384, 192, 0, 0, 384, 192); const d = g.getImageData(0, 0, 384, 192).data;
  const i0 = document.createElement('canvas'); i0.width = 48; i0.height = 192; const h = i0.getContext('2d', {willReadFrequently: true});
  h.drawImage(IMG.character, 0, 0, 48, 192, 0, 0, 48, 192); const s = h.getImageData(0, 0, 48, 192).data;
  const cols = new Set(); for (let i = 0; i < s.length; i += 4) if (s[i + 3]) cols.add(s[i] + ',' + s[i + 1] + ',' + s[i + 2]);
  const out = []; for (let r = 0; r < 4; r++) { const row = []; for (let c = 0; c < 8; c++) { let top = 99, bot = -1, n = 0, alien = 0, half = 0;
    for (let y = 0; y < 48; y++) for (let x = 0; x < 48; x++) { const i = (((r * 48 + y) * 384) + c * 48 + x) * 4; if (!d[i + 3]) continue;
      top = Math.min(top, y); bot = Math.max(bot, y); n++; if (d[i + 3] !== 255) half++; if (!cols.has(d[i] + ',' + d[i + 1] + ',' + d[i + 2])) alien++; }
    row.push([bot - top + 1, bot, alien, half]); } out.push(row); } return [IMG.character.height, out]; }"""


def test_the_jump_has_a_pose_drawn_for_each_part_in_every_facing(game):
    """The jump's own rows (jump_art.js), made from the standing frame by whole rows: the crouch a row shorter, the push
    off a row taller, the landing two shorter, every pose standing on the same row as the cat; no colour the cat has
    not, nothing half seen (never scaled). (It was the run's stride in the air and the frame drawn a row lower.)"""
    h, rows = game.js(POSES)
    assert h == 40 * 48 and game.js("ANIM.jump") == 36 and game.js("JPOSE.settle") == 6
    for facing, row in enumerate(rows):
        stand = row[7][0]
        tall = {pose: row[i][0] - stand for i, pose in enumerate(["crouch", "takeoff", "rise", "apex", "fall", "land", "settle"])}
        assert tall == {"crouch": -1, "takeoff": 1, "rise": -1, "apex": 0, "fall": 2, "land": -2, "settle": -1}, (facing, tall)
        assert len({f[1] for f in row}) == 1 and all(f[2] == 0 and f[3] == 0 for f in row), (facing, row)
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


def test_on_a_phone_the_stick_walks_up_a_step_by_itself(browser, server):
    ctx, g = touch_game(browser, server, 390, 844)
    try:
        step_east(g)
        x, y = g.pos()
        g.touch("touchStart", 80, 600)                                       # left thumb, pushed east, held
        for i in range(1, 6):
            g.touch("touchMove", 80 + i * 8, 600)
            g.sleep(30)
        g.wait(f"myPos().x >= {x + 3}", 4000)
        g.touch("touchEnd")
        g.wait(f"meObs.self.x === myPos().x && meObs.self.z === 1 && meObs.self.x >= {x + 3}", 4000)
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
    assert "Space" in cap, cap
    game.press("Space", 0)
    game.wait(f"meObs.self.x === {x + 3} && meObs.self.z === 1", 4000)
    assert not game.errors, game.errors
