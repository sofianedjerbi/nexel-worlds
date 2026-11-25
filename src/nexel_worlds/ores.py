"""Tool tiers and the land's ores: what a pickaxe of each tier breaks and how fast, and the ores in the stone (where,
how many, what they give). The generator lays them (stone.py ore); digging (sim/underground.py) and the recipes
(tiles.py RECIPES: smelting, the tiered tools) use them."""

from dataclasses import dataclass

# TOOL TIERS: an axe or a pickaxe is of a kind (what Block.tool and needs_tool name) and a tier: wood, stone (the plain
# `axe` and `pickaxe`), iron, titanium. The tier says how long a dig takes with it (TIER_TIME: times the stone tool's
# time) and which ores it can break (ORES: the tier each needs). A pack holds counts, not things with a state: tools
# do not wear out.
TIERS = ("wood", "stone", "iron", "titanium")
TIER_TIME = (1.6, 1.0, 0.6, 0.4)
TOOLS = {f"{t}_{k}" if t != "stone" else k: (k, i) for k in ("axe", "pickaxe") for i, t in enumerate(TIERS)}
TOOL_HITS = {t: (2 if k == "axe" else 1) + i for t, (k, i) in TOOLS.items()}   # half hearts a blow with it: a wood axe 2, a titanium one 5


def tool_kind(item: str | None) -> str | None:
    """What a tool in hand is for: "pickaxe" for any pickaxe, "axe" for any axe; any other item is its own kind."""
    return TOOLS[item][0] if item in TOOLS else item


def tool_time(item: str | None) -> float:
    """A dig's time with this tool in hand, times the stone tool's (1 for anything that is not a tiered tool)."""
    return TIER_TIME[TOOLS[item][1]] if item in TOOLS else 1.0


def best_tool(inventory: dict, kind: str) -> str | None:
    """The highest tier of a kind of tool in a pack (what a dig is done with when none is named), or None."""
    return max((t for t, (k, _) in TOOLS.items() if k == kind and inventory.get(t, 0) > 0), key=lambda t: TOOLS[t][1], default=None)


# THE LAND'S ORES: cells of its stone (stone.py ore), in veins, each between two heights; the pickaxe tier a cell of it
# needs, and what it gives. Coal is fuel (every smelt takes one); copper is for electrical parts (wire); iron for
# tools and armour; gold for money only (coins); titanium for the tier over iron. (`share`: how many of the 4 x 4 x 4
# boxes of stone in its heights hold a vein of it; a vein fills about half its box.)
@dataclass(frozen=True)
class Ore:
    name: str
    item: str
    tier: int
    top: int
    bottom: int
    share: float


ORES = [   # rarest first: where two veins meet, the rarer is the cell's
    Ore("titanium", "titanium_ore", 2, -60, -512, 0.035),
    Ore("gold", "gold_ore", 2, -30, -320, 0.04),
    Ore("copper", "copper_ore", 1, -2, -100, 0.07),
    Ore("iron", "iron_ore", 1, -4, -220, 0.08),
    Ore("coal", "coal", 0, 2, -80, 0.10),
]
ORE_OF = {o.item: o for o in ORES}
# Items renamed when ores came: an old save's are its new ones (sim/core.py, at load)
RENAMED = {"ore": "iron_ore", "ingot": "iron_ingot"}
