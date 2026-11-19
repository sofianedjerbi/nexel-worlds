"""What hides you, four ways (options.js: VIEWS). "depth visualisation is unintuitive", and the user wanted several
to try: V goes from one to the next, and the Picture page has them. Cut away: what is built over you (the house you
are in; in build mode, all over the cursor's floor) is not drawn; outline: its edges only; faded: faint; circle:
faint over you. (They were ways of showing the land in front of you too: the land is blocks now, and behind it you
are seen one way, whichever view: the last test.)"""

from test_e2e_floors import go, house

ROW = "document.querySelector('#menu .row.on .name').textContent"


def test_v_goes_through_the_four_views_and_the_picture_page_has_them(game):
    assert game.js("opt('above')") == "outline"               # (the usual one: "make outline the default")
    seen = []
    for _ in range(4):
        game.press("v", 250)
        seen.append([game.js("opt('above')"), game.toast()])
    assert [s[0] for s in seen] == ["faded", "circle", "cut", "outline"] and "Faded" in seen[0][1] and "Outline" in seen[3][1]
    assert game.js("JSON.parse(localStorage.getItem('megastructure-options') || '{}').above") is None     # (back at the usual one: nothing kept)
    game.press("Escape"); game.press("ArrowDown"); game.press("Enter"); game.press("Tab")
    for _ in range(12):
        if game.js(ROW) == "What hides you":
            break
        game.press("ArrowDown", 40)
    game.press("ArrowRight")
    assert game.js("opt('above')") == "faded"
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


def test_behind_a_hill_you_are_seen_the_same_way_whichever_view(game):
    """The ground in front drawn over you (xray.js): the views were four ways of showing that too (the rock gone, its
    edges drawn, faint, a circle). The land is blocks now and hidden behind it you are seen one way, the rock in
    front of you cut away: whichever view is picked (they still say how a built roof over you is shown), it is as
    much cut, the same tiles, and the screen round you is the same."""
    x, y = game.pos()
    game.stamp(-2, 1, ["....."] * 2, levels=["33333"] * 2)  # a rise three layers high just south of you
    game.wait("xray.a > .98", 8000); game.sleep(400)
    shot = """() => { const keep = {}; for (const f of ['drawEntity', 'drawNameplate', 'drawEmote', 'drawSelector', 'drawIntent']) { keep[f] = window[f]; window[f] = () => null; }
      parts.length = puffs.length = 0; frame(performance.now()); Object.assign(window, keep); const S = TS(), [ox, oy] = screenOrigin(S);
      const d = ctx.getImageData(Math.round((ox + (myPos().x - 4) * S) * DPR), Math.round((oy + (myPos().y - 4) * S) * DPR), Math.round(9 * S * DPR), Math.round(7 * S * DPR)).data;
      let a = 2166136261; for (let i = 0; i < d.length; i++) a = Math.imul(a ^ d[i], 16777619);
      return [+xray.a.toFixed(2), [...xray.pic.cut].sort().join(' '), a >>> 0]; }"""
    got = {}
    for v in ("circle", "cut", "faded", "outline"):
        game.js(f"setOpt('above', '{v}')")
        game.sleep(300)
        got[v] = game.js(shot)
    assert got["circle"][0] > .98 and f"{x},{y + 1},0" in got["circle"][1], got   # the rise in front of you: cut down to your ground
    assert got["cut"] == got["circle"] and got["faded"] == got["circle"] and got["outline"] == got["circle"], got
    assert not game.errors
