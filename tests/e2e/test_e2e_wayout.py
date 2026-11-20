"""The way out of the ground is shown (web/js/wayout.js finds it, wayshow.js draws it): "i dont know how to get out
of that cave", "It looks like we can get out but no evident way or block to break !!"."""

import pytest
from test_e2e_hd_sun import hd

SLOT = "(n) => String((slots.indexOf(n) + 1) % 10)"
CUR = """(() => { const c = WayShow.cur, e = document.getElementById('waycap'), on = !!e && e.style.display === 'block', r = on ? e.getBoundingClientRect() : null;
  const n = c && c.next, a = n && HdLook.screenOf(n.x + .5, n.y + .5, n.z);
  return {shown: !!c, trapped: !!c && c.trapped, digs: c ? c.digs.map((d) => [d.x, d.y, d.z, d.key]) : [], now: c && c.now ? c.now.key : null, way: c && c.path[1] ? c.path[1].d : null,
    steps: c ? c.path.length - 1 : 0, cap: on ? e.textContent : '', off: r && a ? [Math.round(r.x + r.width / 2 - a[0]), Math.round(r.y + r.height - a[1])] : null, out: WayShow.res ? !!WayShow.res.out : null}; })()"""
KEYS = {"N": "ArrowUp", "S": "ArrowDown", "W": "ArrowLeft", "E": "ArrowRight"}
# px of the dashed box round the next block that are the mark's own colours (cream, white), on the world's canvas
BRIGHT = """(() => { const c = WayShow.cur, n = c && c.next; if (!n) return 0; const k = DPR, q = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([i, j]) => HdLook.screenOf(n.x + i, n.y + j, n.z));
  const x0 = Math.min(...q.map((v) => v[0])) - 6, y0 = Math.min(...q.map((v) => v[1])) - 6, w = Math.max(...q.map((v) => v[0])) - x0 + 8, h = Math.max(...q.map((v) => v[1])) - y0 + 30;
  const d = HdLook.read(Math.round(x0 * k), Math.round(y0 * k), Math.round(w * k), Math.round(h * k)).data; let m = 0;
  for (let i = 0; i < d.length; i += 4) if (d[i] > 245 && d[i + 1] > 235 && d[i + 2] > 160) m++; return m; })()"""


# the cap lies on you or on your name (prompts.js keep)
ON_ME = """(() => { const e = document.getElementById('waycap'); if (!e || e.style.display !== 'block') return false; const b = e.getBoundingClientRect();
  return (Prompts.keep || []).some((k) => b.x < k.x + k.w && k.x < b.x + b.width && b.y < k.y + k.h && k.y < b.y + b.height); })()"""
# what the SCREEN says to do: the one cap: a key's name, or an arrow (its way)
CAP = """(() => { const e = document.getElementById('waycap'); if (!e || e.style.display !== 'block') return null; const i = e.querySelector('i'); return e.textContent || (i ? i.className.split(' ')[0] : ''); })()"""


@pytest.mark.quick
def test_at_the_bottom_of_your_own_shaft_the_way_out_is_drawn_and_following_it_gets_you_out(game):
    """Four down in a shaft a tile wide, a pickaxe in hand: the blocks to break are marked, the next one carries its
    key; R breaks it whichever way you face; where the way is a step, you walk it. On the meadow nothing is shown.
    (The classic look: its under-ground view draws the same marks.)"""
    game.clear_area(10)
    x, y = game.pos()
    game.give(pickaxe=1)
    game.press(game.js(SLOT, "pickaxe"))
    game.rest()
    assert not game.js(CUR)["shown"]                               # on the surface: nothing
    game.face(0, 1)
    game.wait("($('actions').innerText + $('prompts').innerText).includes('Dig down')", 3000)
    for depth in (1, 2, 3, 4):
        game.press("x", 100)
        game.wait(f"myAt && myAt.z === {-depth} && !myAction", 8000)
    game.face(-1, 0)                                               # (looking west: the way goes east)
    game.wait("WayShow.cur && WayShow.cur.now && !WayShow.busy", 5000)
    game.frames(3)
    c = game.js(CUR)
    assert c["trapped"] and c["now"] == "up" and c["cap"] == "R" and c["way"] == "E", c
    assert c["digs"][0] == [x + 1, y, -2, "up"] and len(c["digs"]) == 5, c    # the first step's block (the sky is over you), then two a layer; the last layer is a hop
    assert game.actions() == "" and game.js("Marks.list.length") == 0, game.actions()      # one key: the block's (no row beside what you face, no bracket, nothing in the corner)
    presses = 0
    for _ in range(24):
        c = game.js(CUR)
        if not c["shown"]:
            break
        presses += 1
        if c["now"]:
            cell = c["digs"][0]
            game.press({"up": "r", "use": "Space", "alt": "x"}[c["now"]], 100)
            game.wait(f"!solidAt({cell[0]}, {cell[1]}, {cell[2]}) && !myAction", 8000)
        else:
            at = game.js("[myAt.x, myAt.y, myAt.z]")
            game.hold([KEYS[c["way"]]], 90)
            game.wait(f"myAt && (myAt.x !== {at[0]} || myAt.y !== {at[1]}) && !walking", 4000)
        game.wait("!WayShow.busy", 4000)
        game.frames(2)
    s = game.server()
    assert s["z"] == 0 and s["hp"] == 20 and presses <= 12, (s["z"], presses)       # five blocks and the steps between, the last open ones too: shown until you stand on the grass
    game.frames(3)
    c = game.js(CUR)
    assert not c["shown"] and c["cap"] == "" and not game.errors, c


def test_in_a_cave_with_a_way_out_on_foot_nothing_is_drawn_until_you_stand_still(game):
    """A tunnel under a hill, open at its east end: not trapped. Walking: nothing. Standing two seconds: the dots of
    the way to the daylight, and no block to break."""
    game.clear_area(10)
    x, y = game.pos()
    game.stamp(-4, -1, ["....."] * 3, levels=["44440", "40000", "44440"], roofs=["00000", "04440", "00000"])   # three tiles of tunnel west of you into a hill of four; you at its mouth
    game.rpc("dev_teleport", x=x - 3, y=y, z=0)
    game.arrive()
    game.rest()
    assert game.js(f"topAt({x - 3}, {y}) > 0")
    game.hold(["ArrowRight"], 90)
    game.wait(f"myAt && myAt.x === {x - 2} && !walking", 4000)
    assert not game.js(CUR)["shown"]
    game.wait("WayShow.cur", 6000)                                         # two seconds standing
    c = game.js(CUR)
    assert not c["trapped"] and c["digs"] == [] and c["way"] == "E" and c["steps"] >= 2 and c["cap"] == "", c
    game.hold(["ArrowRight"], 600)
    game.wait("myAt && topAt(myAt.x, myAt.y) <= myAt.z && !walking", 4000)
    game.frames(3)
    assert not game.js(CUR)["shown"] and not game.errors


def test_in_the_hd_picture_the_next_block_has_its_dashed_box_and_its_key_on_it(browser, server):
    """Three down in a shaft, the HD look: the key is pinned on the block R will break, the box round it is drawn in
    the marks' own colours; R breaks it though you look the other way; out of the pickaxe's reach nothing is left."""
    g = hd(browser, server)
    g.js("setOpt('hints', true)")
    x, y = g.pos()
    g.give(pickaxe=1)
    g.press(g.js(SLOT, "pickaxe"))
    g.face(0, 1)
    for depth in (1, 2, 3):
        g.press("x", 100)
        g.wait(f"myAt && myAt.z === {-depth} && !myAction", 8000)
    g.face(-1, 0)
    g.wait("WayShow.cur && WayShow.cur.now && !WayShow.busy && !HdLook.busy", 6000)
    g.frames(4)
    c = g.js(CUR)
    assert c["trapped"] and c["cap"] == "R" and c["digs"][0] == [x + 1, y, -1, "up"], c
    assert 12 < abs(c["off"][0]) <= 90 and -50 <= c["off"][1] <= 60 and not g.js(ON_ME), c            # the key: beside that block, not on it, nor on you or your name
    assert g.js(BRIGHT) > 40, g.js(BRIGHT)                                   # its dashed box is in the picture
    assert "Dig on" not in g.actions() and "Dig into" not in g.actions(), g.actions()   # beside what you face: no other key than the block's
    g.press("r", 100)
    g.wait(f"!solidAt({x + 1}, {y}, -1) && !myAction", 8000)
    assert g.js("(() => { const p = ents.get('agent' + myId); return [p.fx, p.fy]; })()") == [1, 0]    # turned to it
    assert not g.errors


@pytest.mark.parametrize("hands", ["plank", "nothing"])
def test_shut_in_with_a_plank_in_hand_or_with_nothing_the_shown_key_gets_you_out(game, hands):
    """"Grey boxes. A tiny dark square over my name. No key works": three down in a shaft a tile wide. With a plank
    in hand and the pickaxe in the bar, and with no pickaxe at all: the block carries its key all the same, that key
    breaks it (with the pickaxe you carry; by hand, slower), no other key is offered, and doing only what the cap
    says (a key, or the arrow's way) ends on the grass. No plank is laid on the way."""
    game.clear_area(10)
    x, y = game.pos()
    if hands == "plank":
        game.give(pickaxe=1, plank=3)
        game.hold_item("plank")
    game.stamp(0, 0, ["."], levels=["c"])
    game.rpc("dev_teleport", x=x, y=y)
    game.arrive()
    game.wait("myAt && myAt.z === -3 && WayShow.cur && WayShow.cur.now && !WayShow.busy", 6000)
    game.frames(3)
    assert game.js("inHand()") == (hands if hands == "plank" else None)
    assert game.js(CAP) == "R" and not game.js(ON_ME) and game.actions() == "", (game.js(CAP), game.actions())
    presses, seen = 0, []
    for _ in range(20):
        game.wait("!WayShow.busy && !myAction && !pendingAct && !walking", 6000)
        game.frames(3)
        cap = game.js(CAP)
        if cap is None:
            break
        assert not game.js(ON_ME) and game.actions() == "", (cap, game.actions())      # (one key on the screen: no "Lay floor", no other digging, no red line)
        presses += 1
        seen.append(cap)
        if cap in KEYS:
            at = game.js("[myAt.x, myAt.y, myAt.z]")
            game.hold([KEYS[cap]], 90)
            game.wait(f"myAt && (myAt.x !== {at[0]} || myAt.y !== {at[1]}) && !walking", 4000)
        else:
            cell = game.js("(() => { const n = WayShow.cur.now; return [n.x, n.y, n.z]; })()")
            game.press({"R": "r", "Space": "Space", "X": "x"}[cap], 100)
            game.wait(f"!solidAt({cell[0]}, {cell[1]}, {cell[2]}) && !myAction", 12000)
    s = game.server()
    assert s["z"] == 0 and s["hp"] == 20 and seen.count("R") == 3 and presses <= 8, (s["z"], seen)      # a block for the first step, two for the next, the last is a hop
    assert s["inventory"].get("plank", 0) == (3 if hands == "plank" else 0) and not game.errors, s["inventory"]
