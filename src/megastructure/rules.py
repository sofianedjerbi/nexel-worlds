"""The rules a screen has to know, said once: one table made from the server's own constants.

A screen offers what the world will accept ("Fill with dirt", "(slow)", "That won't burn") and walks ahead of it, so
it needs the world's tables. They were typed again in the client, about thirty of them, and four had drifted. Now
`rules_table()` is the only place they are put together, and it goes two ways from here:
  - in the spectator's `hello` (server.py; the demo in a tab runs this same server: browser.py);
  - written out as web/js/rules.js (`uv run python -m megastructure.rules`), because the first screen draws its island
    before any server has answered (in the demo, seconds before Python has even come). A test keeps that file equal
    to this table (tests/test_rules.py), and no table may be typed in the client again.
The client fills its own tables from it (web/js/vocab.js setRules)."""

import json
from pathlib import Path

from . import tiles as T
from .cells import HIGH, LOW, SEA
from .floors import KINDS
from .landblocks import LAND_BLOCKS
from .sim import constants as C
from .sim.climbing import CLIMB, RISE
from .sim.entities import CREATURES
from .sim.leaping import LEAP_G, LEAP_TOP
from .sim.progress import LEVEL
from .sim.storeys import RESTS_ON, STOREY, UPSTAIRS
from .sim.wear import SLOTS
from .sim.wild import BITE_HIGH

FILE = Path(__file__).parent / "web" / "js" / "rules.js"


def char(name: str) -> str:
    return T.GROUNDS[T.G[name]].char if name in T.G else T.BLOCKS[T.B[name]].char


def _said(**kw) -> dict:
    """Only what is so: a tile that is not solid says nothing about it."""
    return {k: v for k, v in kw.items() if v}


def rules_table() -> dict:
    tiles = {g.char: _said(name=g.name, ground=True, walk=g.walkable, liquid=g.liquid, burns=g.flammable, depth=T.DEPTH.get(g.name))
             for g in T.GROUNDS}
    tiles.update({b.char: _said(name=b.name, solid=b.solid, burns=b.flammable, tool=b.tool, needs=b.needs_tool, quick=b.quick,
                                foot=T.FOOTPRINT.get(b.name), upstairs=b.name in UPSTAIRS, holds=b.name in RESTS_ON)
                  for b in T.BLOCKS[1:]})
    sown = {item: "".join(sorted(char(g) for g in T.SEED_GROUNDS)) for item, block in T.PLACEABLE.items() if block == "sprout"}
    return {
        "tiles": tiles,
        # what an item in hand becomes: a thing on the tile (its char), a block built over it (its kind: floors.py),
        # a seed in tilled soil, or the ground itself (ground -> the ground it makes)
        "place": {**{item: char(block) for item, block in T.PLACEABLE.items() if item not in sown},
                  **{k: k for k in KINDS if k not in T.FILLERS}},
        "sown": sown,
        "fills": {item: {char(g): char(to) for g, to in fill.items()} for item, fill in T.FILLERS.items()},
        "land_blocks": list(LAND_BLOCKS),
        "food": T.FOOD, "feed": T.FEED, "weapons": T.WEAPONS, "crops": T.CROPS,
        "wear": T.WEAR, "slots": list(SLOTS),
        "hp_max": C.HP_MAX, "food_max": C.FOOD_MAX, "sprint_food": C.SPRINT_FOOD, "can_size": C.CAN_SIZE,
        "pace": C.PACE, "swim_pace": C.SWIM_PACE, "eat_pace": C.EAT_PACE, "flee_stride": C.FLEE_STRIDE, "spring_s": C.SPRING_S,
        "aside": list(C.ASIDE), "meanwhile": list(C.MEANWHILE),
        "low": LOW, "high": HIGH, "sea": SEA, "storey": STOREY, "day_ticks": C.DAY_TICKS,
        "climb": {"max": CLIMB, "rise": list(RISE), "s": C.CLIMB_S},
        "reach": T.REACH, "long": T.LONG, "wide": {k: v["wide"] for k, v in CREATURES.items() if "wide" in v}, "layer": C.LAYER,
        "leap": {"g": LEAP_G, "top": LEAP_TOP}, "fall_safe": C.FALL_SAFE, "bite_high": BITE_HIGH,
        "level": list(LEVEL),
        "recipes": {k: {"inputs": r.inputs, "output": r.output, "station": r.station} for k, r in T.RECIPES.items()},
    }


def rules_js() -> str:
    return ("// The world's rules, as the server has them. Written by `uv run python -m megastructure.rules` from rules.py: do not\n"
            "// edit it by hand (tests/test_rules.py keeps it equal). The server's hello says the same table again (vocab.js).\n"
            "const RULES = " + json.dumps(rules_table(), separators=(",", ":"), sort_keys=True) + ";\n")


if __name__ == "__main__":
    FILE.write_text(rules_js())
    print(f"wrote {FILE} ({FILE.stat().st_size} bytes)")
