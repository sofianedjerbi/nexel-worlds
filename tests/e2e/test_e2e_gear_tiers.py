"""A tool of a tier shows its tier's metal in the paw, in a chop and in a cut, not only on its icon (#393, the owner's
answer 3; tool_art.js inTier): the four greys of a tool's metal become the tier's, iron keeps them."""

import pytest
from test_e2e_hand import TOOL

pytestmark = pytest.mark.e2e

GREY = {"129,129,129", "183,183,183", "158,170,182", "226,232,236"}
METAL = {"wood": ["7a5236", "b88a5c", "a0714a", "c99a6e"], "stone": ["5d6260", "8a8f8c", "6e7470", "a3a8a0"],
         "copper": ["93502c", "d9844f", "c06a3a", "f2b27e"], "titanium": ["6f8db3", "a9c6e6", "7f9fc6", "e6f2ff"]}
METAL = {t: {",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4)) for h in hs} for t, hs in METAL.items()}
TIERS = ("wood", "stone", "copper", "iron", "titanium")


def item(tier, kind):
    return kind if tier == "stone" and kind != "sword" else f"{tier}_{kind}"


@pytest.mark.parametrize("kind, act", [("pickaxe", None), ("axe", "dig"), ("sword", None), ("sword", "attack")])
def test_a_tool_shows_its_tiers_metal_held_chopping_and_cutting(game, kind, act):
    """Each tier's tool drawn on you (characters.js and held.js, the frame drawn at once on a canvas of its own: no
    frame's timing in it, the same at 16 ms a frame as at 200): its metal's px are its tier's colours, none of them iron's
    greys (iron: its greys, none of another tier's colours)."""
    others = set().union(*METAL.values())
    for tier in TIERS:
        for face in ([0, 1], [1, 0]):
            r = game.js(TOOL, [item(tier, kind), face, act])
            got = {c for _, _, c, _ in r["px"]}
            state = f"{item(tier, kind)} {act or 'held'} facing {face}: colours {sorted(got)}"
            if tier == "iron":
                assert got & GREY and not got & others, f"iron's greys, not another tier's metal: {state}"
            else:
                assert len(got & METAL[tier]) >= 2 and not got & GREY, f"{tier}'s metal, not iron's greys: {state}"
