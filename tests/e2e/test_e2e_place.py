"""The place you are in under ground, as it is seen (web/js/xray.js xrayPlace, xrayFind; voxels.js): what is of it
(all that is open onto your room, a step to it or not), that its floors are on the screen, who is drawn over it and
who is not. (Its light: test_e2e_underground.py.)"""

from test_e2e_digging import DRAWN, LAND, SEEN, earth, green


def test_what_is_dug_under_high_ground_is_seen_and_no_more_one_block_dug_opens_one_block(game):
    """"im breaking only 1 bloc why the whole column is deleted ??": doben4's tunnel under a mountain. What is of the
    place is what was dug: one block dug at the tunnel's end and that tile's floor is of the place, a layer lower for
    the block under it, the tile past it not; the land over it is still there in the world, and the new floor is on the screen, earth."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)                # high ground, three layers
    game.stamp(0, 0, ["......."], levels=["dddddd3"], roofs=["0777770"], heads=["0222220"])   # a pit at its foot, a tunnel from it under the high ground
    X = x + 5                                                 # the tunnel's end: seven layers of land over its floor
    game.rpc("dev_teleport", x=X, y=y, z=-4)
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000)
    assert game.js(f"[seenUnder({X}, {y}), seenUnder({X + 1}, {y})]") == [-4, None]
    for z, floor in ((-2, -3), (-3, -4)):                     # dug on a tile from there, a block, then the one under it:
        col = game.js(f"JSON.stringify(colAt({X + 1}, {y}))")
        assert game.rpc("act", tool="dig", args={"x": X + 1, "y": y, "z": z})["ok"]
        game.wait(f"JSON.stringify(colAt({X + 1}, {y})) !== '{col}'", 20000)
        game.wait(f"{DRAWN} && xray.pic && xray.pic.floor.get('{X + 1},{y}') === {floor}", 20000)
        assert game.js(f"[topAt({X + 1}, {y}), seenUnder({X + 2}, {y})]") == [3, None]     # (the world over it; and no more of the place)
        game.sleep(400)
        dug, past = game.js(LAND, [[X + 1, y, floor, 8, 8], [X + 2, y, floor, 8, 8]])
        assert earth(dug) and not earth(past), (z, dug, past)  # the room dug: its floor on the screen; past it, none
    assert not game.errors


def test_who_walks_over_a_tunnel_goes_with_its_roof_shadow_and_all_and_who_is_beside_it_stays(game):
    """"mobs dispawn on top of tunnel. they should only if they cover the visible part of the tunnel. and their shadow
    should dispawn also": whoever stood over the place was not drawn, and their shadow lay there by itself. The roof
    is lifted off all of the place you are in (xray.js: cut): who stands on land that is cut away under their feet
    goes with it, shadow and all (they would stand in the air), and only they: who stands on the same hill two tiles
    from the cut, on land that is whole, is as anyone on the land; who walks from the one onto the other fades over
    the crossing."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)                # high ground, three layers
    game.stamp(0, 0, ["......."], levels=["dddddd3"], roofs=["0777770"], heads=["0222220"])   # a tunnel under it from a pit at its foot
    X = x + 3
    game.rpc("dev_teleport", x=X, y=y - 2, z=3)               # on the high ground: two hens put there
    game.wait(f"myAt && myAt.x === {X} && myAt.z === 3", 8000)
    over = game.spawn("chicken", 0, 2, still=10 ** 6)         # one on the tunnel's roof
    beside = game.spawn("chicken", 0, 0, still=10 ** 6)       # one two tiles north of it: on land that stays
    game.rpc("dev_teleport", x=X, y=y, z=-4)                  # in the tunnel, under the first
    game.wait(f"myAt && myAt.x === {X} && myAt.z === -4", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    game.wait(f"ents.has('chicken{over}') && ents.has('chicken{beside}')", 8000)
    fade = lambda hen: game.js(f"xrayOverBody(ents.get('chicken{hen}'))")
    assert game.js(f"[seenUnder({X}, {y}), xrayCutAt({X}, {y - 2}), ents.get('chicken{over}').ty, ents.get('chicken{beside}').ty]") == [-4, None, y, y - 2]
    assert fade(over) > .9 and fade(beside) == 0, (fade(over), fade(beside))
    # one that walks from the whole land onto the roof goes little by little over the crossing: no pop
    step = lambda fy: game.js(f"xrayOverBody({{x: {X}, y: {fy}, e: {{kind: 'chicken', id: -1}}, zAt: {{x: {X}, y: Math.round({fy}), z: 3}}}})")
    walk = [step(y - 1 + q / 4) for q in range(5)]
    assert walk[0] == 0 and walk[4] > .9 and walk == sorted(walk) and 0 < walk[1] < walk[2] < walk[3] < walk[4], walk
    game.js("setOpt('shader', 'natural')")                    # their shadows: the second one's is there, the first's is gone with it
    game.wait("Sun.shades() === true", 8000); game.sleep(400)
    # (the shadows' px over the high ground round the two hens, with both, without the one beside, without the one over: one moment)
    both, less_beside, less_over = game.js("""([x, y, over, beside]) => { const raf = window.requestAnimationFrame; window.requestAnimationFrame = () => 0; const T = performance.now(), S = TS(), [ox, oy] = screenOrigin(S);
      const count = () => { frame(T); const d = Sun.layerData(), w = cv.width; let n = 0;
        const x0 = Math.round((ox + (x - 2) * S) * DPR), x1 = Math.round((ox + (x + 3) * S) * DPR), y0 = Math.round((oy + (y - 4) * S - shOf(3) * zoom) * DPR), y1 = Math.round((oy + (y + 2) * S - shOf(3) * zoom) * DPR);
        for (let r = Math.max(0, y0); r < Math.min(cv.height, y1); r++) for (let c = Math.max(0, x0); c < Math.min(w, x1); c++) if (d[(r * w + c) * 4 + 3]) n++; return n; };
      const without = (id) => { const k = 'chicken' + id, p = ents.get(k); ents.delete(k); const n = count(); ents.set(k, p); return n; };
      const out = [count(), without(beside), without(over)]; window.requestAnimationFrame = raf; raf(frame); return out; }""", [X, y, over, beside])
    assert less_over == both and less_beside < both - 20, (both, less_beside, less_over)
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
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    assert game.js(f"[landAt(-7, {X - 1}, {y}, {X}, {y}), xray.pic.floor.size]") == [None, 5]      # a wall, three layers; and all five tiles of the tunnel are of the place
    assert game.js(f"[1, 2, 3, 4].map((d) => seenUnder({X} - d, {y}))") == [-4, -4, -4, -4]
    tunnel = game.js(LAND, [[X - d, y, -4, 8, 8] for d in (1, 2, 3, 4)])          # its floor, from beside you to its other end: on the screen, earth
    assert all(earth(c) for c in tunnel), tunnel
    assert not game.errors


def test_the_floor_you_stand_on_is_seen_under_a_higher_floor_drawn_over_it(game):
    """Two layers are a tile up the screen: a floor two layers over yours and a tile in front of it is drawn on your
    own tile. Down a hole at the north end of a tunnel you stood on the tunnel's floor, to look at, and it went on
    south of you. Your own floor is seen: on the screen, where you stand, earth, a floor."""
    game.clear_area(12)
    x, y = game.pos()
    game.rpc("dev_time", phase=.4)
    game.stamp(1, -4, ["." * 9] * 9, levels=["3" * 9] * 9)
    X = x + 5
    for d, f in enumerate([-8, -6, -5, -4]):                  # a tunnel going down north, then two layers at once: you, there
        game.rpc("dev_col", tiles=[[X, y - 2 + d]], col=[f, f + 3, 3])
    game.rpc("dev_teleport", x=X, y=y - 2, z=-8)
    game.wait(f"myAt && myAt.y === {y - 2} && myAt.z === -8", 8000)
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    assert game.js(f"[seenUnder({X}, {y - 2}), seenUnder({X}, {y - 1})]") == [-8, -6]
    mine = game.js(LAND, [[X, y - 2, -8, 8, 8]])[0]
    assert earth(mine), mine
    assert not game.errors


def test_a_step_is_shut_from_a_room_too_low_to_jump_in_and_open_from_beside_it(game):
    """"doben4 visualizatino issue: why i can't go up bu i cna climb from the left ?": the room he stood in was one
    layer high and the step north of him one layer up: a jump needs room over your head. From the tile beside the
    step, three high, he climbed it. The picture drew that step the same from both. "the roof above the player
    should be indicated in some way". The page knows the world's ways as the server does: no way up that step from
    your room, one from the room beside it, one where there is room to jump; and all seven tiles are of the place.
    (Of five ways drawn for him he took a line on the step's edge, painted with the cut through the ground: the land
    is blocks now, nothing draws that line.)"""
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
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    assert game.js(f"[landAt(-7, {X}, {y - 1}, {X}, {y}), landAt(-7, {X}, {y - 1}, {X - 1}, {y - 1}), landAt(-7, {X + 2}, {y - 1}, {X + 2}, {y}), xray.pic.floor.size]") == [None, -6, -6, 7]
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
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    assert game.js(f"[landAt(-7, {x + 5}, {y}, {x + 4}, {y}), xray.pic.floor.size]") == [None, 6]       # a wall east of you; and all six tiles are of the place
    assert game.js(f"[2, 3, 4, 5, 6, 7].map((i) => seenUnder({x} + i, {y}))") == [-7, -7, -7, -4, -4, -4]   # yours where you are under it, the upper one past there
    upper = game.js(LAND, [[x + 5, y, -4, 8, 8], [x + 6, y, -4, 8, 8], [x + 7, y, -4, 8, 8]])      # its floor, past where it is over you, on to its end: on the screen, earth
    assert all(earth(c) for c in upper), upper
    assert not game.errors


def test_a_floor_stands_on_its_wall_whatever_is_under_it_and_nothing_of_the_place_is_seen_through(game):
    """"the vizualisation issue is still bad. as doben4 i still dont see the exit. i dont see how to go up, where to
    dig to escape": a hole with a low nook, and his tunnel going by three layers over the hole's floor, rock between
    the two. The tunnel's floor was drawn against the nook's, the same earth, a line between: the floor he stood on
    going on east. What is open onto your room is of the place at its own height, step or no step: the tunnel three
    layers over your hole, your hole under it. (Its front, a wall under the higher floor, was painted with the cut
    through the ground; the land is blocks now.)"""
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
    game.wait(DRAWN, 8000); game.wait(SEEN, 20000); game.sleep(300)
    assert game.js(f"[landAt(-9, {X + 1}, {y}, {X}, {y}), xray.pic.floor.size, seenUnder({X}, {y}), seenUnder({X + 1}, {y})]") == [None, 8, -9, -6]
    nook, pit = game.js(LAND, [[X, y - 1, -9, 8, 8], [X - 2, y, -9, 8, 8]])       # your nook and the pit, level with you: on the screen, earth
    assert earth(nook) and earth(pit), (nook, pit)
    assert not game.errors
