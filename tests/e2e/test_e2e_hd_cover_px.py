"""What stands in front of you makes you show through only where it covers your body on the screen (hd_level.js covered)."""
from test_e2e_hd_behind import calm, tidy
from test_e2e_hd_sun import hd


def test_you_show_through_what_stands_in_front_only_where_it_covers_you(browser, server):
    """What stands south of you makes you show through, one px in two, when it covers your body on the screen: its own px'
    box over a quarter of yours or more (hd_level.js covered). A tree or a bush just south does; a flower at your feet,
    a rock, a tree two tiles off to the side do not. (It was "anything standing within two rows south and a column
    each side": a flower two tiles south of you switched the pass on, and you showed through the land in front too.)"""
    g = hd(browser, server)
    calm(g)
    x, y = g.pos()
    got = {}
    for name, (dx, dy, c) in {"flower south": (0, 1, "f"), "flower two south": (0, 2, "f"), "rock south": (0, 1, "M"), "bush south": (0, 1, "b"),
                              "tree south": (0, 1, "T"), "tree two south": (0, 2, "T"), "tree beside": (1, 0, "T"), "tree two south, two east": (2, 2, "T")}.items():
        g.stamp(-4, -4, ["." * 9] * 9)
        g.stamp(dx, dy, [c])
        g.rest(); g.frames(3)
        got[name] = (g.js("HdLook.hid"), round(g.js("HdLook.catSeen()"), 2))
    assert {k: v[0] for k, v in got.items()} == {"flower south": 0, "flower two south": 0, "rock south": 0, "bush south": 1, "tree south": 1, "tree two south": 1,
                                                  "tree beside": 0, "tree two south, two east": 0}, got
    assert .3 < got["tree south"][1] < .9 and got["flower south"][1] > .95, got       # (through the tree: one px in two of you; by the flower: whole)
    tidy(g, x, y)
