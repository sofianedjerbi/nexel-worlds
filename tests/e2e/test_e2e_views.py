"""What hides you, four ways (options.js: VIEWS). "depth visualisation is unintuitive", and the user wanted several
to try: V goes from one to the next, and the Picture page has them. Cut away: what is over you (the house you are in;
in build mode, all over the cursor's floor) is not drawn, nor what is in front of you; outline: their edges only;
faded: faint; circle: faint over you, and a circle round you seen through what is in front (as it was)."""

from test_e2e_floors import go, house

ROW = "document.querySelector('#menu .row.on .name').textContent"


def test_v_goes_through_the_four_views_and_the_picture_page_has_them(game):
    assert game.js("opt('above')") == "cut"                   # (the one the user chose)
    seen = []
    for _ in range(4):
        game.press("v", 250)
        seen.append([game.js("opt('above')"), game.toast()])
    assert [s[0] for s in seen] == ["outline", "faded", "circle", "cut"] and "Outline" in seen[0][1] and "Cut away" in seen[3][1]
    assert game.js("JSON.parse(localStorage.getItem('megastructure-options') || '{}').above") is None     # (back at the usual one: nothing kept)
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter"); game.press("Tab")
    for _ in range(12):
        if game.js(ROW) == "What hides you":
            break
        game.press("ArrowDown", 40)
    game.press("ArrowRight")
    assert game.js("opt('above')") == "outline"
    game.press("Escape"); game.press("Escape")


def test_in_a_house_what_is_over_you_is_cut_away_outlined_or_faint(game):
    x, y = game.pos()
    x0, y0 = x + 2, y - 7
    house(game, x0, y0)
    alpha = lambda *cells: game.js("(cs) => cs.map(([x, y, z]) => Floors.alpha(x, y, z))", [list(c) for c in cells])
    floor, roof = (x0 + 3, y0 + 2, 3), (x0 + 3, y0 + 2, 6)
    go(game, x0 + 3, y0 + 2, 0)                                # in the room, two storeys over you
    edges = """() => new Promise((ok) => { let n = 0; const was = ctx.fillRect.bind(ctx); ctx.fillRect = (...a) => { if (ctx.fillStyle === Structures.INK.toLowerCase()) n++; return was(...a); };
      requestAnimationFrame(() => requestAnimationFrame(() => { ctx.fillRect = was; ok(n); })); })"""
    got = {}
    for v in ("cut", "outline", "faded", "circle"):
        game.js(f"setOpt('above', '{v}')")
        got[v] = [alpha(floor, roof), game.js(edges)]
    assert got["cut"][0] == [0, 0] and got["outline"][0] == [0, 0] and got["faded"][0] == [.12, .12] and got["circle"][0] == [.12, .12], got
    assert got["outline"][1] > got["cut"][1] + 8, got        # the outline: the blocks' edges drawn in the walls' ink
    game.js("setOpt('above', 'cut')")                          # in build mode from upstairs, the floor under yours: all over it is cut away
    go(game, x0 + 2, y0 + 2, 3)
    game.press("b")
    game.js(f"Build.S.at = {{x: {x0 + 3}, y: {y0 + 2}}}")       # (over the room, not the stairs)
    game.press("q")
    assert game.js("[Build.level(), Build.rows()[0][1]]") == [0, "BUILD · -3 · leave"] and alpha(floor) == [0]
    game.press("e")
    assert alpha(floor) == [1]
    game.press("b")


def test_behind_a_hill_the_rock_in_front_is_gone_its_edges_drawn_or_faint(game):
    """The ground in front drawn over you (xray.js): the circle clears it towards you; the other views, all over its
    picture: gone (cut away, outline: and its edges drawn), or a share of it (faded)."""
    x, y = game.pos()
    game.stamp(-2, 1, ["....."] * 2, levels=["33333"] * 2)  # a rise three layers high just south of you
    game.wait("xray.a > .9", 8000)
    at = lambda: game.js("[xrayAt(xray.x, xray.y), xrayAt(xray.x + 2.5, xray.y)]")
    shot = """() => new Promise((ok) => requestAnimationFrame(() => { const c = cv.getContext('2d'), S = TS(), [ox, oy] = screenOrigin(S);
      const d = c.getImageData(Math.round((ox + (myPos().x - 2) * S) * DPR), Math.round((oy + (myPos().y - 1) * S) * DPR), Math.round(5 * S * DPR), Math.round(3 * S * DPR)).data;
      let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] === 0x75 && d[i + 1] === 0x4c && d[i + 2] === 0x60) n++; ok(n); }))"""
    got = {}
    for v in ("circle", "cut", "faded", "outline"):
        game.js(f"setOpt('above', '{v}')")
        game.sleep(300)
        got[v] = [round(a, 2) for a in at()] + [game.js(shot)]
    assert got["circle"][0] > .9 and got["circle"][1] < got["circle"][0], got     # the circle: clear by you, less so further out
    assert got["cut"][:2] == [1, 1] and got["outline"][:2] == [1, 1] and got["faded"][:2] == [.65, .65], got
    assert got["outline"][2] > got["cut"][2] + 20, got       # the rock's edges, in the walls' ink
    assert not game.errors
