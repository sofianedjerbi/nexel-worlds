"""One target, one box (#360): facing a tree with an axe in hand, what X takes down is shown once, by the corners round
the whole tree (hd_marks.js), not also by a block-high box on its tile inside them (target.js)."""
from test_e2e_hd_sun import hd
from test_e2e_target import stage
from test_e2e_wild import shot

# the frame's marks: the aim's corners (HdLook.aim), the cell the key in focus acts on (Target.sel), the boxes drawn
# (Target.drew, but those another mark stands for: under your sprite, the way out's, your own block, the corners')
MARKS = """(() => { const s = Target.sel, a = HdLook.aim, drawn = (d) => !d.bracketed && !d.under && !d.way && !d.mine;
  return {aim: !!a, sel: s && [s.key, s.x, s.y], boxes: Target.drew.filter(drawn).map((d) => [d.key, d.x, d.y]),
    bracketed: Target.drew.filter((d) => d.bracketed).map((d) => [d.key, d.x, d.y])}; })()"""


def test_facing_a_tree_with_an_axe_draws_its_corners_and_no_box_inside(browser, server):
    """The tree east of you, an axe in hand: X's cell is the tree's tile (what the key takes), its corners are drawn
    round the whole tree, and no box is drawn on that tile inside them."""
    game = hd(browser, server)
    game.give(axe=1)
    stage(game, "tree")
    game.hold_item("axe")
    x, y = game.pos()
    game.until(f"Target.sel && Target.sel.key === 'alt' && Target.sel.x === {x + 1} && Target.sel.y === {y} && !!HdLook.aim")   # (the frame that aims at it)
    game.rest()
    m = game.js(MARKS)
    shot(game, "one_target")
    assert m["aim"] and m["sel"] == ["alt", x + 1, y], m
    assert m["boxes"] == [], m                                    # (the owner's picture: a solid square, crown and trunk, inside the corners)
    assert m["bracketed"] == [["alt", x + 1, y]], m
