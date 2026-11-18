"""The place you are in under ground, as it is seen (web/js/xray.js xrayPlace, xraycut.js): what is of it (all
that is open onto your room, a step to it or not), how much of it shows (what was dug, no more), who is drawn over
it and who is not. (Its edge, its light, its walls: test_e2e_underground.py.)"""

from test_e2e_digging import DRAWN, SEEN
from test_e2e_underground import DOWN, PIC

# is a px of the picture one of its lines? [x, y, level: a tile as drawn; ax, ay: the px in it]
LINE = """([x, y, lv, ax, ay]) => { const P = xray.pic, X = x * 16 + ax - P.x, Y = y * 16 - shOf(lv) + ay - P.y;
  return xrayEdges(P).getContext('2d').getImageData(X, Y, 1, 1).data[3] > 0; }"""
# how much of a px of the picture is there, 0 to 255 (all of it: "why the hell there's transparency")
KEPT = """([x, y, lv, ax, ay]) => { const P = xray.pic; return P.over.getContext('2d').getImageData(x * 16 + ax - P.x, y * 16 - shOf(lv) + ay - P.y, 1, 1).data[3]; }"""


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


def test_a_floor_too_high_to_climb_shows_its_front_its_layers_and_its_edge(game):
    """"still hardly understandable: why can't i go up ? why cant i climb right ?", in a hole at the end of a tunnel
    that goes down a layer a tile: height is how far up the screen a floor is drawn, and nothing else said it. The
    floor two layers over yours was a tile on along a strip of earth, the wall behind you the same brown as the
    floor. Told in words it was "explicit guiding.. it should be intuitive, visible". A floor higher than the one
    beside it shows its front, the layers it stands on, each with its seam; where that is two or more nobody climbs
    it and its edge has a line; and a floor is lighter than a wall, as far down as it goes."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)                # high ground, three layers
    game.stamp(0, 0, ["......."], levels=["dddddd3"], roofs=["0777770"], heads=["0222220"])   # a tunnel under it
    X = x + 5                                                 # its end: dug down there, three layers under its floor
    game.rpc("dev_col", tiles=[[X, y]], col=[-7, -2, 3])
    game.rpc("dev_teleport", x=X, y=y, z=-7)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -7", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    px, line, lum = lambda *a: game.js(PIC, list(a)), lambda *a: game.js(LINE, list(a)), lambda p: p[1] + p[2] + p[3]
    floor, front = px(X - 1, y, -4, 6, 8), px(X - 1, y, -4, 6, 20)     # the tunnel's last tile, west of you: its floor; under it, its front
    assert floor[0] and front[0] and lum(floor) > 1.3 * lum(front), (floor, front)
    rows = [lum(px(X - 1, y, -4, 6, 16 + a)) for a in range(24)]      # three layers of it, down to your floor: a seam under each
    assert rows[7] < .85 * rows[4] and rows[15] < .85 * rows[12], rows
    assert line(X - 1, y, -4, 6, 39) and not px(X - 1, y, -4, 6, 40)[0]     # ...and there the cut ends
    assert line(X - 1, y, -4, 15, 8) and line(X - 1, y, -4, 15, 20) and line(X - 1, y, -4, 15, 36)   # its edge beside you: down its floor's side and its front's
    assert not line(X - 2, y, -4, 15, 8) and not line(X - 1, y, -4, 6, 15) and not line(X - 1, y, -4, 6, 16)   # none between two tiles you walk, none between a floor and its own front
    wall, soil = game.js("[colsOf(hillSheet(-12)).bands, colsOf(dugSheet('soil', 12)).top]")    # far down: a floor is told from a wall, a wall's seam from the wall
    assert sum(soil[:3]) > 1.6 * sum(wall[1][:3]) and sum(wall[2][:3]) < .75 * sum(wall[1][:3]), (wall, soil)
    assert not game.errors


def test_the_floor_you_stand_on_is_seen_under_a_higher_floor_drawn_over_it(game):
    """Two layers are a tile up the screen: a floor two layers over yours and a tile in front of it is drawn on your
    own tile. Down a hole at the north end of a tunnel you stood on the tunnel's floor, to look at, and it went on
    south of you. Your own floor is seen, and what is drawn under it, layers higher, has its edge."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 5
    for d, f in enumerate([-8, -6, -5, -4]):                  # a tunnel going down north, then two layers at once: you, there
        game.rpc("dev_col", tiles=[[X, y - 2 + d]], col=[f, f + 3, 3])
    game.rpc("dev_teleport", x=X, y=y - 2, z=-8)
    game.wait(f"myAt && myAt.y === {y - 2} && myAt.z === -8", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    assert game.js(f"(() => {{ const P = xray.pic, f = ({y - 2} * 16 + 64 + 8 - P.y) * P.w + {X} * 16 + 8 - P.x; return [P.seen[f], P.lev[f]]; }})()") == [1, -8]
    assert game.js(LINE, [X, y - 2, -8, 8, 16]) and not game.js(LINE, [X, y - 2, -8, 8, 8])
    assert not game.errors


def test_a_step_is_shut_from_a_room_too_low_to_jump_in_and_open_from_beside_it(game):
    """"doben4 visualizatino issue: why i can't go up bu i cna climb from the left ?": the room he stood in was one
    layer high and the step north of him one layer up: a jump needs room over your head. From the tile beside the
    step, three high, he climbed it. The picture drew that step the same from both. "the roof above the player
    should be indicated in some way": of five ways drawn for him he took the edge. Where the world has no way up
    from a lower floor, the step's edge over that floor has the line of where the cut ends; where it has one, none."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 5                 # you, in a room one layer high; a step north of you; west of that step a room three high; east, a step with a high room under it
    for tile, col in (((X - 1, y), [-7, -6, 3]), ((X, y), [-7, -6, 3]), ((X + 1, y), [-7, -4, 3]), ((X + 2, y), [-7, -4, 3]),
                      ((X - 1, y - 1), [-7, -4, 3]), ((X, y - 1), [-6, -3, 3]), ((X + 2, y - 1), [-6, -3, 3])):
        game.rpc("dev_col", tiles=[list(tile)], col=col)
    game.rpc("dev_teleport", x=X, y=y, z=-7)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -7", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    assert game.js(f"[landAt(-7, {X}, {y - 1}, {X}, {y}), landAt(-7, {X}, {y - 1}, {X - 1}, {y - 1}), landAt(-7, {X + 2}, {y - 1}, {X + 2}, {y}), xray.pic.floor.size]") == [None, -6, -6, 7]
    line = lambda *a: game.js(LINE, list(a))
    assert line(X, y - 1, -6, 8, 15)                                             # shut from your room: the step's edge, over the wall behind you
    assert not line(X, y - 1, -6, 0, 8) and not line(X, y - 1, -6, 0, 20)        # open from beside it: none down its floor's side, nor its front's
    assert not line(X + 2, y - 1, -6, 8, 15)                                     # a step with room to jump under it: none
    assert not game.errors


def test_a_tunnel_dug_under_a_tunnel_the_upper_one_is_seen_on_to_its_way_out(game):
    """"see doben4 position ? the cave extend and has an exit, but im unable to see it. sucks.": he had dug a tunnel
    under his tunnel, from a pit at its end. A tile was of the place at one height: where the upper tunnel is over
    the lower one it was not gone through, and none of it was seen past there, the way out with it. A tile that is
    of the place at another height is gone by at this one."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    for i, col in ((2, [-7, -1, 3]), (3, [-7, -5, -4, -1, 3]), (4, [-7, -5, -4, -1, 3]), (5, [-4, -1, 3]), (6, [-4, -1, 3]), (7, [-4, -1, 3])):
        game.rpc("dev_col", tiles=[[x + i, y]], col=col)      # a pit; east of it a tunnel, and under its first two tiles the one you dug: you, at its end
    game.rpc("dev_teleport", x=x + 4, y=y, z=-7)
    game.wait(f"myAt && myAt.x === {x + 4} && myAt.z === -7", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    assert game.js(f"[landAt(-7, {x + 5}, {y}, {x + 4}, {y}), xray.pic.floor.size]") == [None, 6]       # a wall east of you; and all six tiles are of the place
    assert game.js(f"[2, 3, 4, 5, 6, 7].map((i) => seenUnder({x} + i, {y}))") == [-7, -7, -7, -4, -4, -4]   # yours where you are under it, the upper one past there
    seen, r, g, b = game.js(PIC, [x + 6, y, -4, 8, 8])       # its floor, two tiles on: on the screen, earth
    assert seen and r > g, [seen, r, g, b]
    assert not game.errors


def test_a_floor_stands_on_its_wall_whatever_is_under_it_and_nothing_of_the_place_is_seen_through(game):
    """"the vizualisation issue is still bad. as doben4 i still dont see the exit. i dont see how to go up, where to
    dig to escape": a hole with a low nook, and his tunnel going by three layers over the hole's floor, rock between
    the two. The tunnel's floor was drawn against the nook's, the same earth, a line between: the floor he stood on
    going on east. A floor higher than the floor beside it stands on its front, open onto that room or not. (The
    part of the place he could not walk to was then drawn half seen through the rock, without asking him: "weird
    transparancy, path isn't obvious to player.. why the hell there's transparency". Every px of the place is whole.)"""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 4                 # you, in a nook one layer high; south of it your hole, a pit west of that; the tunnel from over the hole on east
    for tile, col in (((X, y - 1), [-9, -8, 3]), ((X - 1, y - 1), [-9, -8, 3]), ((X - 2, y), [-9, -6, 3]), ((X - 1, y), [-9, -8, -7, -4, 3]), ((X, y), [-9, -7, -6, -4, 3]),
                      ((X + 1, y), [-6, -4, 3]), ((X + 2, y), [-6, -4, 3]), ((X + 3, y), [-6, -4, 3])):
        game.rpc("dev_col", tiles=[list(tile)], col=col)
    game.rpc("dev_teleport", x=X, y=y - 1, z=-9)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -9", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.wait("xray.mix >= 1 && !xray.old", 8000)
    assert game.js(f"[landAt(-9, {X + 1}, {y}, {X}, {y}), xray.pic.floor.size, seenUnder({X}, {y}), seenUnder({X + 1}, {y})]") == [None, 8, -9, -6]
    px, kept, lum = lambda *a: game.js(PIC, list(a)), lambda *a: game.js(KEPT, list(a)), lambda p: p[1] + p[2] + p[3]
    floor, front = px(X + 1, y, -6, 8, 8), [px(X + 1, y, -6, 8, 16 + a) for a in range(24)]      # under the tunnel's end beside your hole, the three layers it stands on:
    assert all(p[0] for p in front) and lum(floor) > 1.3 * lum(front[4]) and not px(X + 1, y, -6, 8, 40)[0], (floor, front)
    assert [kept(X, y - 1, -9, 8, 8), kept(X - 2, y, -9, 8, 8), kept(X + 1, y, -6, 8, 20)] + [kept(X + i, y, -6, 8, 8) for i in (1, 2, 3)] == [255] * 6   # your nook, the pit, that front, the tunnel
    assert not game.errors
