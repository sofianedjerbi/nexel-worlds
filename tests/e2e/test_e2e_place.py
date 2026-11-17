"""The place you are in under ground, as it is seen (web/js/xray.js xrayPlace, xraycut.js): what is of it (all
that is open onto your room, a step to it or not), how much of it shows (what was dug, no more), who is drawn over
it and who is not. (Its edge, its light, its walls: test_e2e_underground.py.)"""

from test_e2e_digging import DRAWN, SEEN
from test_e2e_underground import DOWN, PIC


def test_what_is_dug_under_high_ground_is_seen_and_no_more_one_block_dug_opens_one_block(game):
    """"im breaking only 1 bloc why the whole column is deleted ??": doben4's tunnel under a mountain. Behind every
    floor the picture cut the land open up to its top: one block dug at the tunnel's end and seventeen layers of rock
    were gone from the screen (every one still there in the world). What is seen through is what was dug: a floor and
    the wall behind it, as high as its room. The land over the room stays as it is drawn."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)                # high ground, three layers
    game.stamp(0, 0, ["......."], levels=["dddddd3"], roofs=["0777770"], heads=["0222220"])   # a pit at its foot, a tunnel from it under the high ground
    X = x + 5                                                 # the tunnel's end: seven layers of land over its floor
    game.rpc("dev_teleport", x=X, y=y, z=-4)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    # the rows of a tile's column in the picture that are seen through, counted up from the top of its floor
    shown = lambda tx, f: game.js(f"""([x, y, f]) => {{ const P = xray.pic, out = []; for (let up = -15; up < 80; up++) {{ const Y = y * 16 - shOf(f) - up - P.y; if (Y >= 0 && Y < P.h && P.seen[Y * P.w + x * 16 + 8 - P.x]) out.push(up); }} return out; }}""", [tx, y, f])
    assert shown(X, -4) == list(range(-15, 17))               # its floor and the two layers of its wall: not the seven of the land over it
    assert not any(r > g + 20 for r, g, b in game.js(DOWN, [X, y, 8, -22, -12]))      # (there, on the screen: the high ground's grass, a flower: no earth)
    for z, floor, rows in ((-2, -3, 9), (-3, -4, 17)):        # dug on a tile from there, a block, then the one under it:
        col = game.js(f"JSON.stringify(colAt({X + 1}, {y}))")
        assert game.rpc("act", tool="dig", args={"x": X + 1, "y": y, "z": z})["ok"]
        game.wait(f"JSON.stringify(colAt({X + 1}, {y})) !== '{col}'", 20000)
        game.wait(f"{DRAWN} && xray.pic && xray.pic.floor.get('{X + 1},{y}') === {floor} && xray.mix >= 1 && !xray.old", 20000)
        assert shown(X + 1, floor) == list(range(-15, rows)), (z, shown(X + 1, floor))   # a block's worth of the picture, a layer of wall each
        assert game.js(f"topAt({X + 1}, {y})") == 3           # (and of the world)
    assert not game.errors


def test_who_walks_over_a_tunnel_is_seen_unless_drawn_over_what_shows_of_it_and_so_is_their_shadow(game):
    """"mobs dispawn on top of tunnel. they should only if they cover the visible part of the tunnel. and their shadow
    should dispawn also": whoever stood on a tile over the place you are in was not drawn (as when the land over it
    was cut open up to its top), and their shadow lay there by itself. On the land left over a room they are as anyone
    on the land; drawn over what is seen of the place they go, shadow and all."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)                # high ground, three layers
    game.stamp(0, 0, ["......."], levels=["dddddd3"], roofs=["0777770"], heads=["0222220"])   # a tunnel under it from a pit at its foot
    X = x + 3
    game.rpc("dev_teleport", x=X, y=y - 2, z=3)               # on the high ground: two hens put there
    game.wait(f"myAt && myAt.x === {X} && myAt.z === 3", 8000)
    over = game.spawn("chicken", 0, 2, still=10 ** 6)         # one on the tunnel's roof: drawn up on the land, over nothing of the tunnel
    front = game.spawn("chicken", 0, 5, still=10 ** 6)        # one three tiles south of it: drawn where the tunnel is seen
    game.rpc("dev_teleport", x=X, y=y, z=-4)                  # in the tunnel, under the first
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    game.wait(f"ents.has('chicken{over}') && ents.has('chicken{front}')", 8000)
    fade = lambda hen: game.js(f"xrayOverBody(ents.get('chicken{hen}'))")
    assert game.js(f"[seenUnder({X}, {y}), ents.get('chicken{over}').ty, ents.get('chicken{front}').ty]") == [-4, y, y + 3]
    assert fade(over) == 0 and fade(front) > .9, (fade(over), fade(front))
    game.js("setOpt('shader', 'natural')")                    # their shadows: the first one's is there, the second's is gone with it
    game.wait("Sun.shades() === true", 8000); game.sleep(400)
    # (the shadows' px over the high ground from the first hen's row to the second's, with both hens, without the second, without the first: one moment)
    both, less_front, less_over = game.js("""([x, y, over, front]) => { const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0; const T = performance.now(), S = TS(), [ox, oy] = screenOrigin(S);
      const count = () => { frame(T); const d = Sun.layerData(), w = cv.width; let n = 0;
        const x0 = Math.round((ox + (x - 2) * S) * DPR), x1 = Math.round((ox + (x + 3) * S) * DPR), y0 = Math.round((oy + (y - 1) * S - shOf(3) * zoom) * DPR), y1 = Math.round((oy + (y + 5) * S - shOf(3) * zoom) * DPR);
        for (let r = Math.max(0, y0); r < Math.min(cv.height, y1); r++) for (let c = Math.max(0, x0); c < Math.min(w, x1); c++) if (d[(r * w + c) * 4 + 3]) n++; return n; };
      const without = (id) => { const k = 'chicken' + id, p = ents.get(k); ents.delete(k); const n = count(); ents.set(k, p); return n; };
      const out = [count(), without(front), without(over)]; window.requestAnimationFrame = raf; raf(frame); return out; }""", [X, y, over, front])
    assert less_front == both and less_over < both - 20, (both, less_front, less_over)
    game.js("for (const k of Object.keys(OPT_DEFAULT)) setOpt(k, OPT_DEFAULT[k]); localStorage.clear()")
    assert not game.errors


def test_dug_down_at_a_tunnels_end_the_tunnel_over_you_is_still_seen(game):
    """"see doben4 position ? the topology of the space is.. hard to understand . how did he get there ? where's the
    exit ? why the tunnel is invisible ??": the place seen was what you could walk or drop to. Two layers under a
    tunnel's floor, in the hole dug at its end, the tunnel is a wall to climb: it went from the picture, and you
    stood in a pocket in the rock. What is open onto the room you are in is of the place, step or no step."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)                # high ground, three layers
    game.stamp(0, 0, ["......."], levels=["dddddd3"], roofs=["0777770"], heads=["0222220"])   # a tunnel under it from a pit at its foot
    X = x + 5                                                 # its end: dug down there, three layers under its floor
    game.rpc("dev_col", tiles=[[X, y]], col=[-7, -2, 3])
    game.rpc("dev_teleport", x=X, y=y, z=-7)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -7", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    assert game.js(f"[landAt(-7, {X - 1}, {y}, {X}, {y}), xray.pic.floor.size]") == [None, 5]      # a wall, three layers; and all five tiles of the tunnel are of the place
    assert game.js(f"[1, 2, 3, 4].map((d) => seenUnder({X} - d, {y}))") == [-4, -4, -4, -4]
    seen, r, g, b = game.js(PIC, [X - 3, y, -4, 8, 8])       # its floor, three tiles from you: on the screen, earth
    assert seen and r > g, [seen, r, g, b]
    assert not game.errors
