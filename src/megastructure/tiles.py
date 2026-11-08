"""Static tile, item and recipe tables.

Setting: an endless archipelago of grassy islands. People wake up here with nothing; they chop,
dig, farm, build and fence, trade, steal and burn. There are no rules and no safe zones.
Durations (`hardness`, recipe `ticks`) are in tenths of a second.
"""

from dataclasses import dataclass, field

DIRS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


@dataclass(frozen=True)
class Ground:
    name: str
    char: str
    walkable: bool = True
    flammable: bool = False
    diggable: bool = True  # bare-ground dig tills it
    liquid: bool = False


@dataclass(frozen=True)
class Block:
    name: str
    char: str
    solid: bool = True
    flammable: bool = False
    hardness: int = 0  # tenths of a second to dig by hand; 0 = cannot be dug
    drops: dict = field(default_factory=dict)
    tool: str | None = None  # tool that halves dig time
    needs_tool: str | None = None  # tool required to dig at all
    wall: bool = False  # counts as shelter


GROUNDS = [
    Ground("water", "~", walkable=False, diggable=False, liquid=True),
    Ground("bridge", ":"),
    Ground("grass", ".", flammable=True),
    Ground("dirt", ","),
    Ground("tilled", "o"),
    Ground("cobble", "_", diggable=False),
    Ground("ash", "'"),
    Ground("deep_water", "=", walkable=False, diggable=False, liquid=True),
]
G = {g.name: i for i, g in enumerate(GROUNDS)}

BLOCKS = [
    Block("none", " ", solid=False),
    Block("tree", "T", flammable=True, hardness=12, drops={"wood": 3}, tool="axe", wall=True),
    Block("berry_bush", "b", flammable=True, hardness=3, drops={"berries": 2, "seed": 1}),
    Block("rock", "M", hardness=18, drops={"stone": 2}, tool="pickaxe", wall=True),
    Block("ore", "*", hardness=24, drops={"ore": 1, "stone": 1}, needs_tool="pickaxe", wall=True),
    Block("thicket", "H", flammable=True, hardness=5, drops={"fiber": 2}, tool="axe", wall=True),
    Block("mushroom", "Q", solid=False, hardness=2, drops={"mushroom": 1}),
    Block("fence", "#", flammable=True, hardness=8, drops={"fence": 1}, tool="axe", wall=True),
    Block("stone_wall", "%", hardness=30, drops={"stone_wall": 1}, tool="pickaxe", wall=True),
    Block("door", "+", solid=False, flammable=True, hardness=8, drops={"door": 1}, tool="axe", wall=True),
    Block("campfire", "^", hardness=4, drops={"stone": 1}),
    Block("workbench", "&", flammable=True, hardness=8, drops={"workbench": 1}, tool="axe", wall=True),
    Block("sign", "?", solid=False, flammable=True, hardness=3, drops={"sign": 1}),
    Block("flag", "!", solid=False, flammable=True, hardness=3, drops={"flag": 1}),
    Block("fire", "x", solid=False),
    Block("crop", "\"", solid=False, flammable=True, hardness=2, drops={"seed": 1}),
    Block("ripe_crop", "w", solid=False, flammable=True, hardness=2, drops={"wheat": 3, "seed": 2}),
    Block("stump", "t", solid=False, hardness=4, drops={"wood": 1}),
    Block("chest", "C", flammable=True, hardness=8, drops={"chest": 1}, tool="axe", wall=True),
]
B = {b.name: i for i, b in enumerate(BLOCKS)}

# items that place as a block (item name -> block name)
PLACEABLE = {
    "fence": "fence",
    "stone_wall": "stone_wall",
    "door": "door",
    "campfire": "campfire",
    "workbench": "workbench",
    "sign": "sign",
    "flag": "flag",
    "seed": "crop",
    "chest": "chest",
}
# items laid on the ground: item -> (grounds it can cover, resulting ground)
FILLERS = {
    "dirt": ({"tilled", "water"}, "dirt"),
    "stone": ({"dirt", "grass", "tilled", "ash", "bridge"}, "cobble"),
    "plank": ({"water"}, "bridge"),
}
SEED_GROUNDS = {"tilled"}  # seeds only take on tilled soil

FOOD = {"berries": 8, "mushroom": 6, "egg": 10, "meat": 6, "cooked_meat": 25, "wheat": 4, "bread": 30, "milk": 12}

WEAPONS = {"sword": 30, "spear": 18, "axe": 12, "pickaxe": 10}
FIST_DAMAGE = 5


@dataclass(frozen=True)
class Recipe:
    name: str
    inputs: dict
    output: dict
    ticks: int = 4
    station: str | None = None  # block that must be within 2 tiles


RECIPES = {
    r.name: r
    for r in [
        Recipe("workbench", {"wood": 4}, {"workbench": 1}, 6),
        Recipe("plank", {"wood": 1}, {"plank": 2}, 3),
        Recipe("fence", {"wood": 2}, {"fence": 1}, 3),
        Recipe("door", {"wood": 3}, {"door": 1}, 4),
        Recipe("sign", {"wood": 1}, {"sign": 1}, 2),
        Recipe("flag", {"wood": 1, "fiber": 1}, {"flag": 1}, 2),
        Recipe("campfire", {"wood": 3, "stone": 2}, {"campfire": 1}, 4),
        Recipe("torch", {"wood": 1, "fiber": 1}, {"torch": 1}, 2),
        Recipe("rope", {"fiber": 3}, {"rope": 1}, 3),
        Recipe("axe", {"wood": 2, "stone": 2, "fiber": 1}, {"axe": 1}, 6, "workbench"),
        Recipe("pickaxe", {"wood": 2, "stone": 3, "fiber": 1}, {"pickaxe": 1}, 6, "workbench"),
        Recipe("spear", {"wood": 2, "stone": 1, "fiber": 1}, {"spear": 1}, 5, "workbench"),
        Recipe("stone_wall", {"stone": 3}, {"stone_wall": 1}, 5, "workbench"),
        Recipe("chest", {"wood": 6}, {"chest": 1}, 6, "workbench"),
        Recipe("cooked_meat", {"meat": 1}, {"cooked_meat": 1}, 5, "campfire"),
        Recipe("bread", {"wheat": 3}, {"bread": 1}, 5, "campfire"),
        Recipe("ingot", {"ore": 2}, {"ingot": 1}, 10, "campfire"),
        Recipe("sword", {"ingot": 2, "wood": 1}, {"sword": 1}, 8, "workbench"),
    ]
}
